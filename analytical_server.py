from kafka import KafkaConsumer
from flask import Flask, jsonify, render_template_string
import json
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
import queue

app = Flask(__name__)

class EmojiAnalytics:
    def __init__(self, window_size_minutes=3):  # Changed to 3 minutes
        self.window_size = window_size_minutes
        self.emoji_counts = defaultdict(lambda: deque())  # emoji_type -> [(timestamp, count), ...]
        self.total_counts = deque()  # [(timestamp, total_count), ...]
        self.current_minute_counts = defaultdict(int)
        self.current_minute_total = 0
        self.last_minute = datetime.now().replace(second=0, microsecond=0)
        self.lock = threading.Lock()
       
    def add_emoji(self, emoji_type, timestamp_str):
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            timestamp = timestamp.replace(tzinfo=None)  # Remove timezone for consistency
        except:
            timestamp = datetime.now()
           
        current_minute = timestamp.replace(second=0, microsecond=0)
       
        with self.lock:
            # If we've moved to a new minute, save the previous minute's data
            if current_minute > self.last_minute:
                self._save_minute_data()
                self._reset_current_minute()
                self.last_minute = current_minute
           
            # Increment counters for current minute
            self.current_minute_counts[emoji_type] += 1
            self.current_minute_total += 1
   
    def _save_minute_data(self):
        timestamp = self.last_minute
       
        # Save individual emoji counts
        for emoji_type, count in self.current_minute_counts.items():
            self.emoji_counts[emoji_type].append((timestamp, count))
            # Keep only data within the window
            cutoff_time = timestamp - timedelta(minutes=self.window_size)
            while (self.emoji_counts[emoji_type] and
                   self.emoji_counts[emoji_type][0][0] < cutoff_time):
                self.emoji_counts[emoji_type].popleft()
       
        # Save total count
        if self.current_minute_total > 0:
            self.total_counts.append((timestamp, self.current_minute_total))
            # Keep only data within the window
            cutoff_time = timestamp - timedelta(minutes=self.window_size)
            while (self.total_counts and
                   self.total_counts[0][0] < cutoff_time):
                self.total_counts.popleft()
   
    def _reset_current_minute(self):
        self.current_minute_counts.clear()
        self.current_minute_total = 0
   
    def get_emoji_data(self):
        with self.lock:
            # Make sure current minute data is included
            self._save_minute_data()
           
            result = {}
            for emoji_type, data_points in self.emoji_counts.items():
                result[emoji_type] = [
                    {
                        'timestamp': timestamp.isoformat(),
                        'count': count
                    }
                    for timestamp, count in data_points
                ]
            return result
   
    def get_total_data(self):
        with self.lock:
            # Make sure current minute data is included
            self._save_minute_data()
           
            return [
                {
                    'timestamp': timestamp.isoformat(),
                    'count': count
                }
                for timestamp, count in self.total_counts
            ]
   
    def get_current_stats(self):
        with self.lock:
            total_emojis = sum(count for _, count in self.total_counts) + self.current_minute_total
            emoji_totals = defaultdict(int)
           
            for emoji_type, data_points in self.emoji_counts.items():
                emoji_totals[emoji_type] = sum(count for _, count in data_points)
                emoji_totals[emoji_type] += self.current_minute_counts.get(emoji_type, 0)
           
            return {
                'total_emojis': total_emojis,
                'emoji_breakdown': dict(emoji_totals),
                'window_minutes': self.window_size
            }

# Global analytics instance
analytics = EmojiAnalytics()

def kafka_consumer_thread():
    """Background thread to consume Kafka messages"""
    consumer = KafkaConsumer(
        'emoji_topic',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        group_id='analytics_consumer',
        auto_offset_reset='latest'
    )
   
    print("Analytics service started - consuming emoji data...")
   
    for message in consumer:
        if message.value:
            emoji_type = message.value.get('emoji_type')
            timestamp = message.value.get('timestamp')
            if emoji_type and timestamp:
                analytics.add_emoji(emoji_type, timestamp)

# Start Kafka consumer in background thread
consumer_thread = threading.Thread(target=kafka_consumer_thread, daemon=True)
consumer_thread.start()

@app.route('/api/emoji-data')
def get_emoji_data():
    """Get time-series data for all emoji types"""
    return jsonify(analytics.get_emoji_data())

@app.route('/api/total-data')
def get_total_data():
    """Get time-series data for total emoji count"""
    return jsonify(analytics.get_total_data())

@app.route('/api/stats')
def get_stats():
    """Get current statistics"""
    return jsonify(analytics.get_current_stats())

@app.route('/')
def dashboard():
    """Analytics dashboard"""
    return render_template_string(DASHBOARD_HTML)

# HTML template for the analytics dashboard
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emoji Analytics Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }
        .stats-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #2196F3;
        }
        .stat-label {
            color: #666;
            margin-top: 10px;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .chart-title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }
        .chart-placeholder {
            height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #f8f9fa;
            border-radius: 4px;
            color: #666;
            font-size: 1.1em;
        }
        .refresh-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: #2196F3;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover {
            background: #1976D2;
        }
        .loading {
            color: #ff9800;
        }
        .error {
            color: #f44336;
        }
        .success {
            color: #4caf50;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .data-table th, .data-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .data-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
   
    <div class="container">
        <div class="header">
            <h1>📊 Emoji Analytics Dashboard</h1>
            <p>Real-time emoji streaming analytics (3-minute rolling window)</p>
            <div id="status" class="loading">Loading Chart.js...</div>
        </div>
       
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-value" id="totalEmojis">0</div>
                <div class="stat-label">Total Emojis</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="uniqueTypes">0</div>
                <div class="stat-label">Unique Types</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="windowSize">3</div>
                <div class="stat-label">Window (minutes)</div>
            </div>
        </div>
       
        <div class="chart-container">
            <div class="chart-title">Total Emoji Count Over Time</div>
            <div id="totalChart" class="chart-placeholder">
                📈 Chart will appear here once Chart.js loads
            </div>
        </div>
       
        <div class="chart-container">
            <div class="chart-title">Emoji Types Over Time</div>
            <div id="emojiChart" class="chart-placeholder">
                📊 Chart will appear here once Chart.js loads
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">Raw Data (Last 10 Data Points)</div>
            <table class="data-table" id="dataTable">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Total Count</th>
                        <th>Emoji Breakdown</th>
                    </tr>
                </thead>
                <tbody id="dataTableBody">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let totalChart, emojiChart;
        let chartJsLoaded = false;
       
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
        ];

        // Function to load Chart.js dynamically
        function loadChartJs() {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js';
                script.onload = () => {
                    console.log('Chart.js loaded successfully');
                    document.getElementById('status').textContent = 'Chart.js loaded successfully!';
                    document.getElementById('status').className = 'success';
                    resolve();
                };
                script.onerror = () => {
                    console.error('Failed to load Chart.js');
                    document.getElementById('status').textContent = 'Failed to load Chart.js - charts disabled';
                    document.getElementById('status').className = 'error';
                    reject();
                };
                document.head.appendChild(script);
            });
        }

        function createChartElement(containerId) {
            const container = document.getElementById(containerId);
            container.innerHTML = '<canvas></canvas>';
            return container.querySelector('canvas').getContext('2d');
        }
       
        function initCharts() {
            if (!window.Chart) {
                console.log('Chart.js not available, skipping chart initialization');
                return;
            }

            try {
                // Total chart
                const totalCtx = createChartElement('totalChart');
                totalChart = new Chart(totalCtx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Total Emojis per Minute',
                            data: [],
                            borderColor: '#2196F3',
                            backgroundColor: 'rgba(33, 150, 243, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: 'Time'
                                }
                            },
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Count'
                                }
                            }
                        }
                    }
                });
               
                // Emoji types chart
                const emojiCtx = createChartElement('emojiChart');
                emojiChart = new Chart(emojiCtx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: []
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: 'Time'
                                }
                            },
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Count'
                                }
                            }
                        }
                    }
                });

                chartJsLoaded = true;
                console.log('Charts initialized successfully');
                document.getElementById('status').textContent = 'Charts ready!';
            } catch (error) {
                console.error('Error initializing charts:', error);
                document.getElementById('status').textContent = 'Error initializing charts: ' + error.message;
                document.getElementById('status').className = 'error';
            }
        }

        function updateDataTable(totalData, emojiData) {
            const tbody = document.getElementById('dataTableBody');
            tbody.innerHTML = '';
           
            // Get last 10 data points
            const recentData = totalData.slice(-10);
           
            recentData.forEach(item => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = new Date(item.timestamp).toLocaleString();
                row.insertCell(1).textContent = item.count;
               
                // Find emoji breakdown for this timestamp
                let breakdown = [];
                for (const [emojiType, dataPoints] of Object.entries(emojiData)) {
                    const point = dataPoints.find(d => d.timestamp === item.timestamp);
                    if (point && point.count > 0) {
                        breakdown.push(`${emojiType}: ${point.count}`);
                    }
                }
                row.insertCell(2).textContent = breakdown.join(', ') || 'No data';
            });
        }
       
        async function refreshData() {
            try {
                document.getElementById('status').textContent = 'Fetching data...';
                document.getElementById('status').className = 'loading';

                // Fetch stats
                const statsResponse = await fetch('/api/stats');
                const stats = await statsResponse.json();
               
                document.getElementById('totalEmojis').textContent = stats.total_emojis;
                document.getElementById('uniqueTypes').textContent = Object.keys(stats.emoji_breakdown).length;
                document.getElementById('windowSize').textContent = stats.window_minutes;
               
                // Fetch total data
                const totalResponse = await fetch('/api/total-data');
                const totalData = await totalResponse.json();
               
                // Fetch emoji data
                const emojiResponse = await fetch('/api/emoji-data');
                const emojiData = await emojiResponse.json();

                // Update data table
                updateDataTable(totalData, emojiData);

                console.log('Data fetched:', { totalData, emojiData, stats });

                if (chartJsLoaded && totalChart && emojiChart) {
                    // Update total chart
                    totalChart.data.labels = totalData.map(d => new Date(d.timestamp).toLocaleTimeString());
                    totalChart.data.datasets[0].data = totalData.map(d => d.count);
                    totalChart.update();
                   
                    // Update emoji chart
                    const emojiTypes = Object.keys(emojiData);
                    const allTimestamps = [...new Set(
                        Object.values(emojiData).flat().map(d => d.timestamp)
                    )].sort();
                   
                    emojiChart.data.labels = allTimestamps.map(t => new Date(t).toLocaleTimeString());
                    emojiChart.data.datasets = emojiTypes.map((emoji, index) => ({
                        label: emoji,
                        data: allTimestamps.map(timestamp => {
                            const dataPoint = emojiData[emoji].find(d => d.timestamp === timestamp);
                            return dataPoint ? dataPoint.count : 0;
                        }),
                        borderColor: colors[index % colors.length],
                        backgroundColor: colors[index % colors.length] + '20',
                        fill: false,
                        tension: 0.4
                    }));
                    emojiChart.update();

                    document.getElementById('status').textContent = 'Data updated successfully!';
                    document.getElementById('status').className = 'success';
                } else {
                    document.getElementById('status').textContent = 'Data updated (charts disabled)';
                    document.getElementById('status').className = 'success';
                }
               
            } catch (error) {
                console.error('Error fetching data:', error);
                document.getElementById('status').textContent = 'Error fetching data: ' + error.message;
                document.getElementById('status').className = 'error';
            }
        }
       
        // Initialize everything
        async function init() {
            try {
                await loadChartJs();
                initCharts();
            } catch (error) {
                console.log('Charts disabled, continuing with data table only');
            }
           
            // Initial data load
            await refreshData();
           
            // Auto-refresh every 10 seconds
            setInterval(refreshData, 10000);
        }

        // Start initialization when page loads
        init();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("Starting Emoji Analytics Service...")
    print("Dashboard available at: http://localhost:5002")
    print("API endpoints:")
    print("  /api/emoji-data - Time-series data by emoji type")
    print("  /api/total-data - Total emoji count over time")
    print("  /api/stats - Current statistics")
    app.run(port=5002, debug=True, threaded=True)
