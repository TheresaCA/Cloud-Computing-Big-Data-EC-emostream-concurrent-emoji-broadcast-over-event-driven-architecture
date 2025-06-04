# EC-Team-27-emostream-concurrent-emoji-broadcast-over-event-driven-architecture

# EmoStream - Concurrent Emoji Broadcast System

## Features

- **Real-time Emoji Broadcasting**: Stream emojis across multiple clients instantly
- **Event-Driven Architecture**: Built on Apache Kafka for reliable message queuing
- **WebSocket Clustering**: Multi-cluster WebSocket support for scalability
- **Load Testing**: Built-in load testing capabilities with Locust integration
- **Stream Analytics**: Real-time emoji analytics using Apache Spark
- **Web Interface**: Interactive web client for sending and receiving emojis
- **Automated Senders**: Configure automated emoji generators for testing

## 🏗Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │───▶│   API Server    │───▶│   Kafka Topic   │
│   (Flask App)   │    │   (Flask API)   │    │  (emoji_topic)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐           ▼
│  Spark Consumer │◀───│  Cluster Manager│◀──────────────────────
│   (Analytics)   │    │  (WebSockets)   │
└─────────────────┘    └─────────────────┘
```

## 🛠 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/emostream-concurrent-emoji-broadcast.git
cd emostream-concurrent-emoji-broadcast
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install and Start Kafka

#### Download and Start Kafka:
```bash
# Download Kafka
wget https://downloads.apache.org/kafka/2.8.1/kafka_2.13-2.8.1.tgz
tar -xzf kafka_2.13-2.8.1.tgz
cd kafka_2.13-2.8.1

# Start Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# Start Kafka Server (in a new terminal)
bin/kafka-server-start.sh config/server.properties

# Create the emoji topic (in a new terminal)
bin/kafka-topics.sh --create --topic emoji_topic --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
```

### 4. Install Apache Spark
```bash
# Download Spark
wget https://downloads.apache.org/spark/spark-3.3.0/spark-3.3.0-bin-hadoop3.tgz
tar -xzf spark-3.3.0-bin-hadoop3.tgz
export SPARK_HOME=/path/to/spark-3.3.0-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin
```

##  Quick Start

### 1. Start the Core Services

#### Terminal 1: API Server
```bash
python api_server.py
```
*Runs on http://localhost:5000*

#### Terminal 2: WebSocket Cluster Manager
```bash
python pubsub.py
```
*WebSocket servers start on ports 8765, 8766, 8767*

#### Terminal 3: Web Client Interface
```bash
python client.py
```
*Runs on http://localhost:5001*

#### Terminal 4: Spark Analytics (Optional)
```bash
python spark_consumer.py
```

### 2. Access the Web Interface

Open your browser and navigate to `http://localhost:5001`

1. Enter a unique User ID
2. Click "Connect" to join the emoji stream
3. Click emoji buttons to broadcast
4. Use "Start Automated Sender" for continuous emoji generation

##  Testing

### Unit Tests
```bash
python -m unittest emojitest.py
```

### Load Testing with Locust
```bash
# Install locust if not already installed
pip install locust

# Run load test
locust -f locustfile.py --host=http://localhost:5000
```

Access Locust web interface at `http://localhost:8089`

### Built-in Load Testing
Use the web interface at `http://localhost:5001` to trigger load tests:
```bash
curl -X POST http://localhost:5001/load_test \
  -H "Content-Type: application/json" \
  -d '{"duration": 60, "batches_per_second": 5}'
```

##  Monitoring and Analytics

### Kafka Topic Monitoring
```bash
# Check topic details
bin/kafka-topics.sh --describe --topic emoji_topic --bootstrap-server localhost:9092

# Monitor messages
bin/kafka-console-consumer.sh --topic emoji_topic --from-beginning --bootstrap-server localhost:9092
```

### Spark Analytics Dashboard
The Spark consumer provides real-time analytics:
- Emoji count aggregations per minute
- Scaled metrics for high-volume scenarios
- Windowed analytics with watermarking

Access Spark UI at `http://localhost:4040` when running.


## Performance Metrics

The system is designed to handle:
- **1000+ emojis/second per client**
- **100+ concurrent clients**
- **Multi-cluster WebSocket distribution**
- **Real-time Spark analytics processing**
- **Fault-tolerant message queuing**
