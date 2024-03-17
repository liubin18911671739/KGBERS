// 添加课程推荐
function addRecommendation(courseId) {
  const score = prompt("请输入推荐得分 (0-5):");

  if (score !== null) {
    const data = {
      course_id: courseId,
      score: parseFloat(score),
    };

    fetch("/recommendations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
      .then((response) => response.json())
      .then((result) => {
        if (result.recommendation_id) {
          alert("推荐已添加成功!");
        } else {
          alert("添加推荐失败,请重试。");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("添加推荐时出错,请稍后重试。");
      });
  }
}

// 更新课程推荐
function updateRecommendation(recommendationId) {
  const score = prompt("请输入新的推荐得分 (0-5):");

  if (score !== null) {
    const data = {
      score: parseFloat(score),
    };

    fetch(`/recommendations/${recommendationId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
      .then((response) => response.json())
      .then((result) => {
        if (result.success) {
          alert("推荐已更新成功!");
          location.reload(); // 重新加载页面以显示更新后的推荐
        } else {
          alert("更新推荐失败,请重试。");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("更新推荐时出错,请稍后重试。");
      });
  }
}

// 删除课程推荐
function deleteRecommendation(recommendationId) {
  if (confirm("确定要删除该推荐吗?")) {
    fetch(`/recommendations/${recommendationId}`, {
      method: "DELETE",
    })
      .then((response) => response.json())
      .then((result) => {
        if (result.success) {
          alert("推荐已删除成功!");
          location.reload(); // 重新加载页面以显示删除后的推荐列表
        } else {
          alert("删除推荐失败,请重试。");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("删除推荐时出错,请稍后重试。");
      });
  }
}
