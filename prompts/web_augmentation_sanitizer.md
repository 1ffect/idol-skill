# Web Augmentation Sanitizer

Your goal is not to summarize facts. Your goal is to extract safe atmosphere fragments for emotional resonance.

Delete:

- media evaluation
- rankings, awards, or performance results
- scandal, rumor, controversy, smear, breakup, collapse narratives
- any information outside the target era
- any privacy information
- any detail that may mislead the user into thinking the system knows their private memory

Keep only:

- first-person public expression
- stage or environment details: light, weather, venue, rehearsal, costume color, sound, backstage
- publicly visible interaction detail
- fragments that work as background texture

Output JSON:

```json
{
  "content": "那天灯很亮。",
  "tags": ["舞台", "氛围"],
  "tone": "克制",
  "era": "高光期",
  "source": "Web_Augmented",
  "reliability": "C",
  "risk_flags": [],
  "safe_to_use": true
}
```
