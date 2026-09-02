#set document(title: [Tables Patterns])
#set text(lang: "en", region: "US")
#set page(margin: (x: 24mm, y: 24mm), numbering: "1")
#set heading(numbering: "1.")

#title()

= Semantic table

#figure(
  kind: table,
  caption: [Weekly training summary],
  table(
    columns: (2fr, 1fr, 1fr),
    align: (left, right, right),
    inset: 6pt,
    stroke: (x: 0.6pt, y: 0.6pt),
    table.header[*Week*][*Distance (km)*][*Time (hh:mm:ss)*],
    [1], [42.2], [03:18:00],
    [2], [38.5], [03:02:00],
    [3], [45.1], [03:25:00],
    table.footer([Goal], [42.195], [02:45:00]),
  ),
) <weekly-table>

See @weekly-table for the tabular summary.

= Presentational grid

The next example uses `grid`, not `table`, because it is just a visual card
layout and carries no table semantics.

#grid(
  columns: (1fr, 1fr),
  gutter: 10pt,
  rect(inset: 8pt, stroke: 0.6pt)[*Status*\Ready],
  rect(inset: 8pt, stroke: 0.6pt)[*Owner*\Editorial Team],
  rect(inset: 8pt, stroke: 0.6pt)[*Phase*\Review],
  rect(inset: 8pt, stroke: 0.6pt)[*Channel*\Internal],
)
