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

    NLTK_AVAILABLE = True
except Exception:  # pragma: no cover - 取决于运行环境
    NLTK_AVAILABLE = False


STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "this", "that", "is", "are", "be", "as", "by", "from", "at", "it",
    "learn", "learning", "course", "introduction", "intro", "basics",
    "using", "use", "explore", "concepts", "concept", "data",
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+")
MIN_DOCUMENTS = 2


class TopicModelService:
    """
    课程主题抽取。

    优先使用 gensim LDA(需先 `fit` 语料),可选 nltk 分词/停用词;
    依赖缺失或语料不足时降级为词频关键词抽取,保证无 ML 依赖也能运行。
    """

    def __init__(self, top_n=3, num_topics=5):
        self.top_n = top_n
        self.num_topics = num_topics
        self.dictionary = None
        self.lda = None
        self._stopwords = self._load_stopwords()

    def fit(self, documents):
        """在课程语料上训练 LDA;返回是否成功启用 LDA。"""
        # 每次 fit 先清空旧模型,避免语料不足时沿用过期 LDA。
        self.dictionary = None
        self.lda = None

        documents = [doc for doc in documents if doc and doc.strip()]
        if not GENSIM_AVAILABLE or len(documents) < MIN_DOCUMENTS:
            return False

        tokenized = [self.tokenize(doc) for doc in documents]
        tokenized = [tokens for tokens in tokenized if tokens]
        if len(tokenized) < MIN_DOCUMENTS:
            return False

        self.dictionary = corpora.Dictionary(tokenized)
        self.dictionary.filter_extremes(no_below=1, no_above=0.9)
        corpus = [self.dictionary.doc2bow(tokens) for tokens in tokenized]
        if not corpus:
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

    def extract(self, text, top_n=None):
        top_n = top_n or self.top_n
        if self.lda is not None and self.dictionary is not None:
            words = self._lda_topics(text, top_n)
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

    def tokenize(self, text):
        text = (text or "").lower()
        if NLTK_AVAILABLE:
            try:
                raw = nltk.word_tokenize(text)
                # 仅保留字母/数字/汉字 token,丢弃标点等噪声。
                return [
                    token
                    for token in raw
                    if TOKEN_PATTERN.fullmatch(token)
                ]
            except Exception:
                pass
        return TOKEN_PATTERN.findall(text)

    def _load_stopwords(self):
        if NLTK_AVAILABLE:
            try:
                return set(nltk_stopwords.words("english")) | STOPWORDS
            except Exception:
                pass
        return set(STOPWORDS)
