import type { SeriesPoint, VariableName } from "@/types/contracts";

const MAX_BARS = 60;

/**
 * Mini gráfico de barras en SVG para la serie de una variable.
 * Se limita a MAX_BARS barras para no saturar el DOM.
 */
export function SeriesChart({
  series,
  variable,
  unit,
}: {
  series: SeriesPoint[];
  variable: VariableName;
  unit: string;
}) {
  if (!series || series.length === 0) return null;

  const points =
    series.length > MAX_BARS
      ? series.slice(series.length - MAX_BARS)
      : series;

  const values = points.map((point) => point.value);
  const min = Math.min(0, ...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  const width = 300;
  const height = variable === "speed" ? 132 : 72;
  const gap = 1;
  const barWidth = Math.max(1, width / points.length - gap);
  const baseline = height - ((0 - min) / span) * height;
  const chartPoints = points.map((point, index) => {
    const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
    const y = height - 8 - ((point.value - min) / span) * (height - 16);
    return { ...point, x, y };
  });

  return (
    <div className={`chart ${variable === "speed" ? "chart-line" : "chart-bars"}`}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${variable === "speed" ? "Gráfica de línea" : "Gráfica de barras"} de ${points.length} puntos, unidad ${unit}`}
      >
        {variable === "speed" ? (
          <>
            <line x1="0" y1={height - 8} x2={width} y2={height - 8} className="chart-axis" />
            <polyline
              points={chartPoints.map((point) => `${point.x},${point.y}`).join(" ")}
              className="chart-line-path"
            />
            {chartPoints.map((point, index) => (
              <circle key={`${point.t}-${index}`} cx={point.x} cy={point.y} r="3.5" className="chart-point">
                <title>{`t=${point.t} s · ${point.value} ${unit}`}</title>
              </circle>
            ))}
          </>
        ) : (
          points.map((point, index) => {
            const valueHeight = Math.max(1, ((point.value - min) / span) * (height - 8));
            const x = index * (barWidth + gap);
            const y = point.value >= 0 ? height - valueHeight : baseline;
            return (
              <rect key={`${point.t}-${index}`} x={x} y={y} width={barWidth} height={valueHeight} className="chart-bar">
                <title>{`${point.value} ${unit} · ${point.t}`}</title>
              </rect>
            );
          })
        )}
      </svg>
      <div className="small muted">
        {points.length} puntos · {variable === "speed" ? "tiempo" : "tramo/apoyo"}: {points[0].t} → {points[points.length - 1].t} · {unit}
      </div>
    </div>
  );
}
