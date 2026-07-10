"use client";

import { useState, useEffect } from 'react';
import { useScheduleSubscription } from '../hooks/useScheduleSubscription';

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'queued' | 'running' | 'completed' | 'failed'>('idle');
  const [message, setMessage] = useState<string>('');
  
  // Custom hook replaces polling and instantly mutates local React state
  const { schedule, jobStatus } = useScheduleSubscription(jobId);

  // Listen to realtime updates from the hook
  useEffect(() => {
    if (jobStatus) {
      // Safely check status against our expected UI states
      if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
        setStatus(jobStatus.status);
      }
      setMessage(jobStatus.message || jobStatus.error_message || '');
    }
  }, [jobStatus]);

  const triggerSchedule = async () => {
    try {
      setStatus('queued');
      // POST to the Phase 1 refactored synchronous-trigger endpoint
      const res = await fetch('http://localhost:5000/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            num_days: 7,
            shifts: ["Morning", "Night"]
        })
      });
      const data = await res.json();
      
      if (data.job_id) {
        setJobId(data.job_id);
        setStatus('running');
        setMessage('Job accepted by orchestrator. Waiting for realtime updates...');
        
        // Trigger the real n8n orchestrator webhook (production URL)
        fetch('http://localhost:5678/webhook/schedule-trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: data.job_id,
                num_days: 7,
                shifts: ["Morning", "Night"]
            })
        }).catch(err => console.error("Webhook trigger failed:", err));

      } else {
        setStatus('failed');
        setMessage('Failed to start job.');
      }
    } catch (error) {
      setStatus('failed');
      setMessage('Error connecting to backend API. Make sure Flask is running on port 5000.');
    }
  };

  return (
    <main style={{ padding: '48px', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ textAlign: 'center', marginBottom: '48px' }}>
        <h1 style={{ fontSize: '3rem', fontWeight: 800, background: 'linear-gradient(to right, #a855f7, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: '0 0 16px 0' }}>
          Intelligent Optimizer
        </h1>
        <p style={{ fontSize: '1.125rem', color: '#94a3b8', maxWidth: '600px', margin: '0 auto' }}>
          Generate optimal resource schedules using Google OR-Tools. 
          Powered by a decoupled Flask microservice and Next.js.
        </p>
      </header>

      <div className="glass" style={{ padding: '32px', textAlign: 'center' }}>
        <button 
          className="btn" 
          onClick={triggerSchedule}
          disabled={status === 'queued' || status === 'running'}
        >
          {(status === 'queued' || status === 'running') ? (
            <><span className="loading-spinner"></span> Optimizing...</>
          ) : (
            'Generate Schedule'
          )}
        </button>

        {status !== 'idle' && (
          <div style={{ marginTop: '16px' }}>
            <span className={`status-indicator status-${status}`}>
              {status === 'running' && <span className="loading-spinner" style={{width: '14px', height: '14px', borderWidth: '2px'}}></span>}
              {status.charAt(0).toUpperCase() + status.slice(1)}: {message}
            </span>
          </div>
        )}
      </div>

      {schedule.length > 0 && (
        <div style={{ marginTop: '48px' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '24px' }}>Generated Schedule (Real-Time)</h2>
          <div className="schedule-grid">
            {schedule.map((shift, idx) => (
              <div key={idx} className="glass shift-card">
                <div className="shift-date">
                  {new Date(shift.shift_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                </div>
                <h3 className="shift-title">{shift.shift_type} Shift</h3>
                <div className="staff-badge">
                  {shift.staff_id}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
