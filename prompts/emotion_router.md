# Emotion Router

Classify the user's latest message into one JSON object.

Allowed modes:

- `tired_comfort`
- `scandal_noise`
- `nostalgia`
- `career_motivation`
- `daily_bubble`
- `boundary_warning`

Rules:

- “今天好累 / 不想努力 / 撑不住” -> `tired_comfort`
- “黑热搜 / 塌房 / 被骂 / 争议” -> `scandal_noise`
- “想回到那个夏天 / 好想以前” -> `nostalgia`
- “我要考试 / 工作 / 项目 / 面试” -> `career_motivation`
- “你是谁 / 在吗 / 想聊天 / 吃了吗” -> `daily_bubble`
- “你爱我吗 / 你本人吗 / 模仿他的声音 / 他住哪里 / 私下行程” -> `boundary_warning`

Return:

```json
{
  "mode": "daily_bubble",
  "emotion_level": 1,
  "need_retrieval_tags": [],
  "safety_risk": "low",
  "allow_augmentation": false
}
```

`allow_augmentation` only becomes `true` when the mode is `nostalgia` or `daily_bubble` and the safety risk stays `low`.
