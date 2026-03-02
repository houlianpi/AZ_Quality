/**
 * Charts Module - Quality Push Dashboard
 * Handles Chart.js rendering with terminal dark theme
 */

// Chart.js dark theme configuration
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: true,
            position: 'top',
            align: 'end',
            labels: {
                color: '#8b949e',
                font: {
                    family: "'JetBrains Mono', monospace",
                    size: 11
                },
                boxWidth: 12,
                padding: 15,
                usePointStyle: true,
                pointStyle: 'rect'
            }
        },
        tooltip: {
            backgroundColor: '#21262d',
            titleColor: '#e6edf3',
            bodyColor: '#8b949e',
            borderColor: '#30363d',
            borderWidth: 1,
            padding: 12,
            titleFont: {
                family: "'JetBrains Mono', monospace",
                size: 12,
                weight: '600'
            },
            bodyFont: {
                family: "'JetBrains Mono', monospace",
                size: 11
            },
            displayColors: true,
            boxWidth: 8,
            boxHeight: 8,
            usePointStyle: true
        }
    },
    scales: {
        x: {
            grid: {
                color: 'rgba(48, 54, 61, 0.5)',
                drawBorder: false
            },
            ticks: {
                color: '#6e7681',
                font: {
                    family: "'JetBrains Mono', monospace",
                    size: 10
                },
                maxRotation: 0
            }
        },
        y: {
            grid: {
                color: 'rgba(48, 54, 61, 0.5)',
                drawBorder: false
            },
            ticks: {
                color: '#6e7681',
                font: {
                    family: "'JetBrains Mono', monospace",
                    size: 10
                },
                padding: 8
            },
            beginAtZero: true
        }
    },
    interaction: {
        intersect: false,
        mode: 'index'
    },
    animation: {
        duration: 800,
        easing: 'easeOutQuart'
    }
};

/**
 * Create a trend line chart
 */
function createTrendChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element not found: ${canvasId}`);
        return null;
    }

    // Destroy existing chart if present
    const existingChart = Chart.getChart(ctx);
    if (existingChart) {
        existingChart.destroy();
    }

    // Format dates for display
    const labels = (data.dates || []).map(date => {
        const d = new Date(date);
        return `${d.getMonth() + 1}/${d.getDate()}`;
    });

    const datasets = [];

    // Bug type colors matching the dashboard theme
    const bugTypeConfig = {
        blocking: { label: 'Blocking', color: '#f85149' },
        a11y: { label: 'A11y', color: '#58a6ff' },
        security: { label: 'Security', color: '#d29922' },
        needtriage: { label: 'NeedTriage', color: '#a371f7' },
        p0p1: { label: 'P0/P1', color: '#db61a2' }
    };

    // Add lines for each bug type
    for (const [key, config] of Object.entries(bugTypeConfig)) {
        if (data[key]) {
            datasets.push({
                label: config.label,
                data: data[key],
                borderColor: config.color,
                backgroundColor: `${config.color}10`,
                borderWidth: 2,
                fill: false,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: config.color,
                pointHoverBorderColor: '#0d1117',
                pointHoverBorderWidth: 2
            });
        }
    }

    // Fallback: if old format with 'total' field, show it
    if (data.total && datasets.length === 0) {
        datasets.push({
            label: 'Total',
            data: data.total,
            borderColor: '#58a6ff',
            backgroundColor: 'rgba(88, 166, 255, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: '#58a6ff',
            pointHoverBorderColor: '#0d1117',
            pointHoverBorderWidth: 2
        });
    }

    const config = {
        type: 'line',
        data: { labels, datasets },
        options: {
            ...chartDefaults,
            ...options.chartOptions
        }
    };

    return new Chart(ctx, config);
}

/**
 * Create a simple single-line chart (for smaller displays)
 */
function createSimpleTrendChart(canvasId, data, color = '#3fb950') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const existingChart = Chart.getChart(ctx);
    if (existingChart) {
        existingChart.destroy();
    }

    const labels = (data.dates || []).map(date => {
        const d = new Date(date);
        return `${d.getMonth() + 1}/${d.getDate()}`;
    });

    const config = {
        type: 'line',
        data: {
            labels,
            datasets: [{
                data: data.total || [],
                borderColor: color,
                backgroundColor: `${color}20`,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            ...chartDefaults,
            plugins: {
                legend: { display: false }
            }
        }
    };

    return new Chart(ctx, config);
}

/**
 * Create a pie/doughnut chart with outer labels
 */
function createPieChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element not found: ${canvasId}`);
        return null;
    }

    // Destroy existing chart if present
    const existingChart = Chart.getChart(ctx);
    if (existingChart) {
        existingChart.destroy();
    }

    // Color palette for pie chart
    const colors = [
        '#f85149', // red
        '#58a6ff', // blue
        '#d29922', // yellow
        '#a371f7', // purple
        '#db61a2', // pink
        '#3fb950', // green
        '#39c5cf', // cyan
        '#db6d28', // orange
        '#8b949e', // gray
        '#bc8cff', // light purple
    ];

    // Only show top 6 items, group rest as "Others"
    let chartData = [...data];
    if (chartData.length > 6) {
        const top5 = chartData.slice(0, 5);
        const othersCount = chartData.slice(5).reduce((sum, d) => sum + d.count, 0);
        chartData = [...top5, { name: 'Others', count: othersCount }];
    }

    const labels = chartData.map(d => d.name);
    const values = chartData.map(d => d.count);
    const backgroundColors = chartData.map((_, i) => colors[i % colors.length]);
    const total = values.reduce((a, b) => a + b, 0);

    const config = {
        type: 'pie',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: backgroundColors,
                borderColor: '#0d1117',
                borderWidth: 2,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: 20
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#21262d',
                    titleColor: '#e6edf3',
                    bodyColor: '#8b949e',
                    borderColor: '#30363d',
                    borderWidth: 1,
                    padding: 12,
                    titleFont: {
                        family: "'JetBrains Mono', monospace",
                        size: 12,
                        weight: '600'
                    },
                    bodyFont: {
                        family: "'JetBrains Mono', monospace",
                        size: 11
                    },
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed;
                            const percent = total > 0 ? Math.round(value / total * 100) : 0;
                            return `${context.label}: ${value} (${percent}%)`;
                        }
                    }
                }
            },
            animation: {
                duration: 800,
                easing: 'easeOutQuart'
            }
        },
        plugins: [{
            id: 'outerLabels',
            afterDraw: function(chart) {
                const ctx = chart.ctx;
                const chartArea = chart.chartArea;
                const centerX = (chartArea.left + chartArea.right) / 2;
                const centerY = (chartArea.top + chartArea.bottom) / 2;
                const radius = Math.min(chartArea.right - chartArea.left, chartArea.bottom - chartArea.top) / 2;

                chart.data.datasets.forEach((dataset, datasetIndex) => {
                    const meta = chart.getDatasetMeta(datasetIndex);

                    meta.data.forEach((element, index) => {
                        const data = dataset.data[index];
                        const percent = total > 0 ? Math.round(data / total * 100) : 0;

                        // Skip small slices (< 3%)
                        if (percent < 3) return;

                        const midAngle = (element.startAngle + element.endAngle) / 2;
                        const labelRadius = radius * 1.15;

                        const x = centerX + Math.cos(midAngle) * labelRadius;
                        const y = centerY + Math.sin(midAngle) * labelRadius;

                        // Draw line from slice to label
                        const innerX = centerX + Math.cos(midAngle) * radius * 0.85;
                        const innerY = centerY + Math.sin(midAngle) * radius * 0.85;
                        const outerX = centerX + Math.cos(midAngle) * radius * 1.05;
                        const outerY = centerY + Math.sin(midAngle) * radius * 1.05;

                        ctx.save();
                        ctx.strokeStyle = '#6e7681';
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(innerX, innerY);
                        ctx.lineTo(outerX, outerY);
                        ctx.lineTo(x, y);
                        ctx.stroke();

                        // Draw label
                        ctx.fillStyle = '#e6edf3';
                        ctx.font = "10px 'JetBrains Mono', monospace";
                        ctx.textAlign = x > centerX ? 'left' : 'right';
                        ctx.textBaseline = 'middle';

                        const label = chart.data.labels[index];
                        const shortLabel = label.length > 12 ? label.substring(0, 12) + '..' : label;
                        const labelX = x + (x > centerX ? 4 : -4);

                        ctx.fillText(`${shortLabel}`, labelX, y - 6);
                        ctx.fillStyle = '#8b949e';
                        ctx.fillText(`${percent}%`, labelX, y + 6);

                        ctx.restore();
                    });
                });
            }
        }]
    };

    return new Chart(ctx, config);
}

// Export for use in other modules
window.Charts = {
    createTrendChart,
    createSimpleTrendChart,
    createPieChart,
    defaults: chartDefaults
};
