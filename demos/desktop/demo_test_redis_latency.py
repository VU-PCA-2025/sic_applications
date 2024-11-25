from utils.redis_latency_test import RedisLatencyTester

if __name__ == "__main__":
    latency_tester = RedisLatencyTester()
    # test the latency of the redis ping-pong for 20 times
    latency_tester.test_redis_ping_pong_latency(count=20)
