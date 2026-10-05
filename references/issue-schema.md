# 问题数据结构

问题主数据建议使用JSON。必填字段：

```json
{
  "issue_id": "FITOUT-MEP-001",
  "title": "厨房柜体与插座深化顺序未闭合",
  "category": "跨专业协调",
  "discipline": ["精装修", "电气", "家具"],
  "severity": "高",
  "judgement": "interface_open",
  "location": {
    "building": "A栋",
    "floor": "标准层",
    "unit_type": "U1",
    "room": "厨房"
  },
  "finding": "橱柜分格待深化，但插座位置已固定。",
  "evidence": [
    {
      "file": "相对或绝对路径",
      "drawing_no": "ID-P08",
      "layout": "ID-P08",
      "object_handle": "示例句柄",
      "coordinate": [1000, 2000],
      "text": "由橱柜公司深化",
      "snapshot": "evidence/FITOUT-MEP-001-a.png"
    }
  ],
  "basis_rule_ids": ["PROJECT-001"],
  "impact": ["预埋返工", "插座不可操作"],
  "question_to_designer": "请确认插座用途、标高及柜内外属性。",
  "suggested_action": "橱柜、机电和厨电联合会签深化图。",
  "required_information": ["厨电型号", "橱柜深化图"],
  "confidence": 0.91,
  "status": "open",
  "reviewer": "AI预审/人工复核人",
  "created_at": "YYYY-MM-DD"
}
```

状态建议：`open`、`answered_pending_drawing`、`drawing_updated_pending_review`、`closed`、`accepted_risk`、`duplicate`。

问题关闭需要回复或改图证据；仅有口头说明不得自动关闭。

问题与检查结果分开存储。没有发现问题的检查也记录`check_id、scope、rule_id、result、evidence、review_status`，以证明覆盖。
