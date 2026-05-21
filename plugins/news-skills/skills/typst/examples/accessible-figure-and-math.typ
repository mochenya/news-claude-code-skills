#set document(title: [Accessible Figure and Math Example])
#set text(lang: "en", region: "US")
#set page(margin: (x: 30mm, y: 25mm), numbering: "1")

#title()

This example shows decorative content marked as an artifact, a semantic figure
with caption and alt text, and accessible block math.

#pdf.artifact[
  #place(top + right, dx: -10pt, dy: 6pt, circle(radius: 10pt, fill: luma(230)))
]

#figure(
  alt: "Blue outlined five-point star",
  caption: [Curve-based figure that needs a textual alternative.],
  curve(
    stroke: blue,
    curve.move((25pt, 0pt)),
    curve.line((10pt, 50pt)),
    curve.line((50pt, 20pt)),
    curve.line((0pt, 20pt)),
    curve.line((40pt, 50pt)),
    curve.close(),
  ),
) <star-fig>

See @star-fig for the figure example.

#math.equation(
  block: true,
  alt: "d S equals delta q divided by T",
  $ dif S = (delta q) / T $,
)
