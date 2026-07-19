"use client";

import * as React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { cssVarAsHsl } from "@/utils/design-tokens";

/** Single-series categorical bar chart (one series: question count per
 * AI provider) — a single hue is correct here since color doesn't
 * need to distinguish anything beyond the axis labels already showing
 * (dataviz skill: "color follows the entity", and a one-series chart
 * needs no legend). */
export function AiUsageChart({
  data,
}: {
  data: { provider: string; count: number }[];
}) {
  const [barColor, setBarColor] = React.useState("hsl(217 91% 60%)");
  const [gridColor, setGridColor] = React.useState("hsl(217 33% 17%)");
  const [textColor, setTextColor] = React.useState("hsl(215 20% 65%)");

  React.useEffect(() => {
    setBarColor(cssVarAsHsl("--primary"));
    setGridColor(cssVarAsHsl("--border"));
    setTextColor(cssVarAsHsl("--foreground-muted"));
  }, []);

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-foreground-muted">
        No AI usage recorded yet.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
        <CartesianGrid horizontal={false} stroke={gridColor} />
        <XAxis
          type="number"
          tick={{ fill: textColor, fontSize: 12 }}
          axisLine={{ stroke: gridColor }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="provider"
          tick={{ fill: textColor, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={80}
        />
        <Tooltip
          cursor={{ fill: "transparent" }}
          contentStyle={{
            background: cssVarAsHsl("--popover"),
            border: `1px solid ${gridColor}`,
            borderRadius: 8,
          }}
          labelStyle={{ color: textColor }}
        />
        <Bar dataKey="count" fill={barColor} radius={[0, 4, 4, 0]} barSize={20}>
          <LabelList
            dataKey="count"
            position="right"
            fill={textColor}
            fontSize={12}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
