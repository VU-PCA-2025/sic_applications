import json
import os
import time

import mysql.connector
import numpy as np
import redis
import speedtest
from dotenv import load_dotenv
from mysql.connector import Error


class RedisLatencyTester:
    """
    Utility class to test Redis ping-pong latency, internet download/upload speed,
    and store the latency data in MySQL.
    """

    def __init__(self):
        # Get the aws redis settings from environment variables.
        load_dotenv()
        self.redis_host = os.getenv("AWS_REDIS_HOST")
        self.redis_username = os.getenv("AWS_REDIS_USERNAME")
        self.redis_password = os.getenv("AWS_REDIS_PASSWORD")
        self.redis_latencies = []
        self.e2e_latencies = []

    def end_to_end_latency_test(self, published_timestamp, average_count=100):
        """
        end-to-end application latency test

        :param published_timestamp: timestamp of the published message
        :param average_count: number of messages to average the latency, default is 100
        """

        latency = time.time() - published_timestamp
        self.e2e_latencies.append(latency)
        # print(f"End-to-End Latency for this message: {latency*1000:.6f} ms")
        if len(self.e2e_latencies) % average_count == 0:
            print(
                f"Average End-to-End Latency: {sum(self.e2e_latencies) / len(self.e2e_latencies) *1000:.6f} ms"
            )
            self.e2e_latencies = []

    def test_redis_ping_pong_latency(
        self, host="localhost", port=6379, password="changemeplease", count=20
    ):
        """
        Measures the Redis ping-pong latency

        :param host: Redis server hostname
        :param port: Redis server port
        :param count: Number of PINGs to send
        :return: List of latencies in milliseconds
        """
        try:
            # if aws redis_host is not provided in .env, fall back to local Redis
            if self.redis_host is None:
                client_redis = redis.Redis(
                    host=host, port=port, password=password, decode_responses=False
                )
            else:
                client_redis = redis.Redis(
                    host=self.redis_host,
                    port=port,
                    ssl=True,
                    decode_responses=False,
                    username=self.redis_username,
                    password=self.redis_password,
                    ssl_cert_reqs=None,
                    socket_timeout=5,
                )

            if not client_redis.ping():
                print("Failed to connect to Redis.")
                return

            print("Connected to Redis.")

            for _ in range(count):
                start_time = time.time()
                client_redis.ping()
                latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                self.redis_latencies.append(latency)
            avg_latency = sum(self.redis_latencies) / len(self.redis_latencies)
            print(f"Ping latencies (ms): {self.redis_latencies}")
            # filtered_latencies = remove_outliers(latencies)
            # avg_latency = np.mean(filtered_latencies)
            # print(f"Filtered latencies (ms): {filtered_latencies}")
            print(f"Average latency: {avg_latency:.2f} ms")

            # # Store in MySQL (optional)
            # self.store_latency_in_mysql(self.redis_latencies, avg_latency)

        except redis.ConnectionError as e:
            print(f"Redis connection error: {e}")

    def perform_speed_test(self):
        """
        Perform internet speed test
        """
        st = speedtest.Speedtest(secure=True)
        servers = st.get_best_server()
        # print(f"Best server details: {servers}")
        print("Testing download speed...")
        download_speed = st.download() / 1000000  # Convert to Mbps
        print("Testing upload speed...")
        upload_speed = st.upload() / 1000000
        return download_speed, upload_speed

    def get_mysql_connection(self):
        try:
            # Connect to MySQL
            connection = mysql.connector.connect(
                host=os.getenv("MYSQL_HOST"),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
            )

            if connection.is_connected():
                print("Successfully connected to MySQL")

                cursor = connection.cursor()

                # Check if the database exists
                cursor.execute("SHOW DATABASES LIKE 'latency_test'")
                result = cursor.fetchone()

                if result:
                    print("Database 'latency_test' already exists.")
                else:
                    # If the database doesn't exist, create it
                    cursor.execute("CREATE DATABASE latency_test")
                    print("Database 'latency_test' created successfully.")
                return connection

        except Error as e:
            print(f"Error: {e}")

    def store_latency_in_mysql(self, latencies, avg_latency):
        """
        Store the latency data in MySQL

        :param latencies: List of latency values in milliseconds
        :param avg_latency: Average latency value in milliseconds
        """
        connection = self.get_mysql_connection()
        if not connection:
            print("Unable to connect to MySQL. Data will not be stored.")
            return

        try:
            cursor = connection.cursor()

            # Switch to the 'latency_test' database
            cursor.execute("USE latency_test;")

            # Ensure the table exists
            create_table_query = """
            CREATE TABLE IF NOT EXISTS redis_latency (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                latencies TEXT,
                average_latency FLOAT
            );
            """
            cursor.execute(create_table_query)

            # Insert data
            insert_query = """
            INSERT INTO redis_latency (latencies, average_latency)
            VALUES (%s, %s);
            """

            # Here we can store latencies as a JSON string
            latencies_json = json.dumps(latencies)

            cursor.execute(insert_query, (latencies_json, avg_latency))
            connection.commit()

            print("Latency data stored in MySQL.")
        except Error as e:
            print(f"Error while inserting data into MySQL: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("MySQL connection closed.")

    def remove_outliers(self, latencies):
        # Calculate Q1 (25th percentile) and Q3 (75th percentile)
        Q1 = np.percentile(latencies, 25)
        Q3 = np.percentile(latencies, 75)

        # Calculate the IQR (Interquartile Range)
        IQR = Q3 - Q1

        # Define bounds for outliers
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        # Filter out outliers
        filtered_latencies = [
            latency for latency in latencies if lower_bound <= latency <= upper_bound
        ]

        return filtered_latencies
