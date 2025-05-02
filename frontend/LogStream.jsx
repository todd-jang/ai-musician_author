import React, { useEffect, useState } from 'react';

const LogStream = () => {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const eventSource = new EventSource("http://localhost:8000/stream/logs");

    eventSource.onmessage = (event) => {
      setLogs((prevLogs) => [...prevLogs.slice(-49), event.data]); // 최신 50개 유지
    };

    eventSource.onerror = (err) => {
      console.error("SSE 연결 오류", err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🌸 실시간 백엔드 로그</h2>
      <div style={styles.logBox}>
        {logs.map((log, idx) => (
          <div key={idx} style={styles.logLine}>{log}</div>
        ))}
      </div>
    </div>
  );
};

const styles = {
  container: {
    fontFamily: "'Gowun Batang', serif",
    background: "#fdf6e3",
    border: "1px solid #e0dccc",
    borderRadius: "12px",
    padding: "1rem",
    width: "400px",
    height: "300px",
    overflowY: "scroll",
    boxShadow: "0px 4px 8px rgba(0,0,0,0.1)"
  },
  title: {
    margin: "0 0 1rem 0",
    color: "#8b5e3c",
    textAlign: "center"
  },
  logBox: {
    fontSize: "0.85rem",
    lineHeight: "1.4rem",
    color: "#333",
  },
  logLine: {
    paddingBottom: "0.2rem"
  }
};

export default LogStream;
