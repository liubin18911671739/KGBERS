import os
import re

try:  # 可选重型依赖:缺失时自动降级为词频抽取
    from gensim import corpora
    from gensim.models import LdaModel

    GENSIM_AVAILABLE = True
except Exception:  # pragma: no cover - 取决于运行环境
    GENSIM_AVAILABLE = False

try:
    import nltk
    from nltk.corpus import stopwords as nltk_stopwords
    from nltk.stem import WordNetLemmatizer

    NLTK_AVAILABLE = True
except Exception:  # pragma: no cover - 取决于运行环境
    NLTK_AVAILABLE = False

try:  # 可选:scikit-learn LDA 后端
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import CountVectorizer

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - 取决于运行环境
    SKLEARN_AVAILABLE = False

try:  # 可选:中文分词,缺失时回退正则
    import jieba

    JIEBA_AVAILABLE = True
except Exception:  # pragma: no cover - 取决于运行环境
    JIEBA_AVAILABLE = False


STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "this", "that", "is", "are", "be", "as", "by", "from", "at", "it",
    "learn", "learning", "course", "introduction", "intro", "basics",
    "using", "use", "explore", "concepts", "concept", "data",
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+")
MIN_DOCUMENTS = 2

# TOPIC_MODEL_BACKEND=auto|gensim|sklearn|frequency
BACKEND_AUTO = "auto"
BACKEND_GENSIM = "gensim"
BACKEND_SKLEARN = "sklearn"
BACKEND_FREQUENCY = "frequency"
_VALID_BACKENDS = (BACKEND_AUTO, BACKEND_GENSIM, BACKEND_SKLEARN, BACKEND_FREQUENCY)


def _configured_backend():
    backend = (os.environ.get("TOPIC_MODEL_BACKEND") or BACKEND_AUTO).strip().lower()
    return backend if backend in _VALID_BACKENDS else BACKEND_AUTO


class TopicModelService:
    """
    课程主题抽取。

    降级链(可用 TOPIC_MODEL_BACKEND 指定单一后端):
      gensim LDA → sklearn LDA → 词频关键词抽取。
    可选增强:jieba 中文分词、nltk 词形还原;依赖缺失时逐级回退,
    保证无 ML 依赖也能运行。
    """

    def __init__(self, top_n=3, num_topics=5, backend=None):
        self.top_n = top_n
        self.num_topics = num_topics
        self.backend = backend or _configured_backend()
        # gensim 后端状态
        self.dictionary = None
        self.lda = None
        # sklearn 后端状态
        self._sk_vectorizer = None
        self._sk_lda = None
        self._stopwords = self._load_stopwords()
        self._lemmatizer = None

    # ---------- 训练 ----------

    def fit(self, documents):
        """在课程语料上训练主题模型;返回是否成功启用 LDA。"""
        # 每次 fit 先清空旧模型,避免语料不足时沿用过期 LDA。
        self.dictionary = None
        self.lda = None
        self._sk_vectorizer = None
        self._sk_lda = None

        documents = [doc for doc in documents if doc and doc.strip()]
        if len(documents) < MIN_DOCUMENTS:
            return False

        tokenized = [self.tokenize(doc) for doc in documents]
        tokenized = [tokens for tokens in tokenized if tokens]
        if len(tokenized) < MIN_DOCUMENTS:
            return False

        if self.backend in (BACKEND_AUTO, BACKEND_GENSIM):
            if self._fit_gensim(tokenized):
                return True
        if self.backend in (BACKEND_AUTO, BACKEND_SKLEARN):
            if self._fit_sklearn(tokenized):
                return True
        return False

    def _fit_gensim(self, tokenized):
        if not GENSIM_AVAILABLE:
            return False
        try:
            self.dictionary = corpora.Dictionary(tokenized)
            self.dictionary.filter_extremes(no_below=1, no_above=0.9)
            corpus = [self.dictionary.doc2bow(tokens) for tokens in tokenized]
            if not corpus:
                self.dictionary = None
                return False

            num_topics = min(self.num_topics, max(1, len(tokenized) - 1))
            self.lda = LdaModel(
                corpus=corpus,
                id2word=self.dictionary,
                num_topics=num_topics,
                passes=5,
                random_state=42,
            )
            return True
        except Exception:  # pragma: no cover - 训练异常时降级
            self.dictionary = None
            self.lda = None
            return False

    def _fit_sklearn(self, tokenized):
        if not SKLEARN_AVAILABLE:
            return False
        try:
            texts = [" ".join(tokens) for tokens in tokenized]
            # 语料已分词/小写化,这里按空格切分即可。
            self._sk_vectorizer = CountVectorizer(
                tokenizer=str.split,
                preprocessor=lambda doc: doc,
                lowercase=False,
                token_pattern=None,
                stop_words=sorted(self._stopwords),
                ngram_range=(1, 2),
            )
            matrix = self._sk_vectorizer.fit_transform(texts)
            if matrix.shape[1] == 0:
                self._sk_vectorizer = None
                return False

            num_topics = min(self.num_topics, max(1, matrix.shape[0] - 1))
            self._sk_lda = LatentDirichletAllocation(
                n_components=num_topics,
                max_iter=10,
                learning_method="online",
                random_state=42,
            )
            self._sk_lda.fit(matrix)
            return True
        except Exception:  # pragma: no cover - 训练异常时降级
            self._sk_vectorizer = None
            self._sk_lda = None
            return False

    # ---------- 抽取 ----------

    def extract(self, text, top_n=None):
        top_n = top_n or self.top_n
        if self.lda is not None and self.dictionary is not None:
            words = self._lda_topics(text, top_n)
            if words:
                return words
        if self._sk_lda is not None and self._sk_vectorizer is not None:
            words = self._sklearn_topics(text, top_n)
            if words:
                return words
        return self.frequency_keywords(text, top_n)

    def _lda_topics(self, text, top_n):
        tokens = self.tokenize(text)
        if not tokens:
            return []
        bow = self.dictionary.doc2bow(tokens)
        if not bow:
            return []
        topic_id = max(
            self.lda.get_document_topics(bow, minimum_probability=0.0),
            key=lambda item: item[1],
        )[0]
        return [word for word, _ in self.lda.show_topic(topic_id, topn=top_n)]

    def _sklearn_topics(self, text, top_n):
        tokens = self.tokenize(text)
        if not tokens:
            return []
        vector = self._sk_vectorizer.transform([" ".join(tokens)])
        if vector.nnz == 0:
            return []
        topic_id = max(
            enumerate(self._sk_lda.transform(vector)[0]),
            key=lambda item: item[1],
        )[0]
        feature_names = self._sk_vectorizer.get_feature_names_out()
        top_indices = self._sk_lda.components_[topic_id].argsort()[::-1][:top_n]
        return [feature_names[i] for i in top_indices]

    def frequency_keywords(self, text, top_n=None):
        top_n = top_n or self.top_n
        counts = {}
        for token in self.tokenize(text):
            # 保留单字中文,过滤单字符英文/数字噪声。
            is_cjk = bool(re.fullmatch(r"[\u4e00-\u9fff]+", token))
            if token in self._stopwords or (len(token) < 2 and not is_cjk):
                continue
            counts[token] = counts.get(token, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [token for token, _ in ranked[:top_n]]

    # ---------- 分词 / NLP 增强 ----------

    def tokenize(self, text):
        text = (text or "").lower()
        # 含中文时优先 jieba 分词(nltk 对 CJK 不切分,会让整句成为一个 token)。
        if JIEBA_AVAILABLE and re.search(r"[\u4e00-\u9fff]", text):
            tokens = [
                token
                for token in jieba.lcut(text)
                if token and TOKEN_PATTERN.fullmatch(token)
            ]
            return self._lemmatize(tokens)
        if NLTK_AVAILABLE:
            try:
                raw = nltk.word_tokenize(text)
                # 仅保留字母/数字/汉字 token,丢弃标点等噪声。
                tokens = [token for token in raw if TOKEN_PATTERN.fullmatch(token)]
                return self._lemmatize(tokens)
            except Exception:
                pass
        if JIEBA_AVAILABLE:
            # jieba 处理中英混排;再过滤标点等噪声 token。
            return [
                token
                for token in jieba.lcut(text)
                if token and TOKEN_PATTERN.fullmatch(token)
            ]
        return TOKEN_PATTERN.findall(text)

    def _lemmatize(self, tokens):
        """可选 nltk 词形还原(英文);词库缺失或异常时原样返回。"""
        if not NLTK_AVAILABLE or not tokens:
            return tokens
        if self._lemmatizer is None:
            try:
                self._lemmatizer = WordNetLemmatizer()
            except Exception:  # pragma: no cover
                return tokens
        try:
            return [self._lemmatizer.lemmatize(token) for token in tokens]
        except Exception:  # pragma: no cover - wordnet 语料缺失时降级
            return tokens

    def _load_stopwords(self):
        if NLTK_AVAILABLE:
            try:
                return set(nltk_stopwords.words("english")) | STOPWORDS
            except Exception:
                pass
        return set(STOPWORDS)
