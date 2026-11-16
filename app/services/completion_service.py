"""课程完成/已学状态的统一查询。

历史上 ``Recommendation`` 同时承担「用户已评价/已学」的语义,学习路径和推荐
排除逻辑都直接读它。自适应学习引入 ``Interaction`` 后,完成事件必须进入同一
套状态,否则「标记为已完成」不会影响推荐和学习路径。

这里保留 ``Recommendation`` 作为向后兼容的「已学」信号,并与
``Interaction(event_type='complete')`` 求并集。
"""

from app import db
from app.models.interaction import EVENT_COMPLETE, Interaction
from app.models.recommendation import Recommendation


def completed_course_ids(user_id):
    """返回用户已学/已完成的课程 id 集合(去重)。"""
    rated = {
        rec.course_id
        for rec in Recommendation.query.filter_by(user_id=user_id).all()
    }
    completed = {
        course_id
        for (course_id,) in db.session.query(Interaction.course_id)
        .filter_by(user_id=user_id, event_type=EVENT_COMPLETE)
        .distinct()
        .all()
    }
    return rated | completed
