import React, { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';

/**
 * DriftChart - Inline bar chart showing policy drift over time.
 * Rendered inside MessageBubble when response contains drift_timeline.
 */
const DriftChart = ({ timeline, maxDrift, policyId }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!timeline || timeline.length === 0) return;
    
    // Cleanup previous chart instance
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext('2d');
    
    // Prepare data
    const labels = timeline.map(t => `${t.from_year}→${t.to_year}`);
    const driftScores = timeline.map(t => t.drift_score);
    
    // Color based on severity
    const backgroundColors = timeline.map(t => {
      if (t.severity === 'CRITICAL') return 'rgba(220, 38, 38, 0.8)';  // red
      if (t.severity === 'HIGH') return 'rgba(249, 115, 22, 0.8)';     // orange
      if (t.severity === 'MEDIUM') return 'rgba(234, 179, 8, 0.8)';    // yellow
      if (t.severity === 'LOW') return 'rgba(34, 197, 94, 0.8)';       // green
      return 'rgba(156, 163, 175, 0.8)';                               // gray
    });

    const borderColors = timeline.map(t => {
      if (t.severity === 'CRITICAL') return 'rgb(220, 38, 38)';
      if (t.severity === 'HIGH') return 'rgb(249, 115, 22)';
      if (t.severity === 'MEDIUM') return 'rgb(234, 179, 8)';
      if (t.severity === 'LOW') return 'rgb(34, 197, 94)';
      return 'rgb(156, 163, 175)';
    });

    chartInstance.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Policy Drift Score',
          data: driftScores,
          backgroundColor: backgroundColors,
          borderColor: borderColors,
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const t = timeline[context.dataIndex];
                return [
                  `Drift: ${(t.drift_score * 100).toFixed(1)}%`,
                  `Severity: ${t.severity}`,
                  `Samples: ${t.samples_year1} → ${t.samples_year2}`
                ];
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 1,
            title: {
              display: true,
              text: 'Drift Score',
              font: { size: 10 }
            },
            ticks: {
              font: { size: 9 }
            }
          },
          x: {
            title: {
              display: true,
              text: 'Year Transition',
              font: { size: 10 }
            },
            ticks: {
              font: { size: 9 },
              maxRotation: 45
            }
          }
        }
      }
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [timeline]);

  if (!timeline || timeline.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          📊 {policyId} Policy Evolution
        </h4>
        {maxDrift && (
          <span className={`
            text-[10px] uppercase font-bold px-2 py-0.5 rounded
            ${maxDrift.severity === 'CRITICAL' ? 'bg-red-100 text-red-700' :
              maxDrift.severity === 'HIGH' ? 'bg-orange-100 text-orange-700' :
              'bg-yellow-100 text-yellow-700'}
          `}>
            Max: {maxDrift.from_year}→{maxDrift.to_year} ({maxDrift.severity})
          </span>
        )}
      </div>
      
      <div className="h-48">
        <canvas ref={chartRef}></canvas>
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-2 mt-2 text-[10px]">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded bg-red-500"></span> Critical (&gt;70%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded bg-orange-500"></span> High (45-70%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded bg-yellow-500"></span> Medium (25-45%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded bg-green-500"></span> Low (&lt;25%)
        </span>
      </div>
    </div>
  );
};

export default DriftChart;
