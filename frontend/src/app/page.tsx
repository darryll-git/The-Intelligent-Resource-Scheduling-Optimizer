"use client";

import { useState, useEffect } from 'react';
import { useScheduleSubscription } from '../hooks/useScheduleSubscription';

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'queued' | 'running' | 'completed' | 'failed'>('idle');
  const [message, setMessage] = useState<string>('');
  
  const [targetMonth, setTargetMonth] = useState<number>(new Date().getMonth() + 1);
  const [targetYear, setTargetYear] = useState<number>(new Date().getFullYear());
  
  // Custom hook replaces polling and instantly mutates local React state
  const { schedule, jobStatus } = useScheduleSubscription(jobId, targetMonth, targetYear);

  // Derive unique dates and staff for the matrix view
  const uniqueDates = Array.from(new Set(schedule.map((s: any) => s.shift_date.split('T')[0]))).sort() as string[];
  // Pre-define shift types for the Y-axis
  const shiftTypes = ['morning', 'afternoon', 'evening', 'night'];

  // Helper to get ALL staff assigned to a specific shift type and date
  const getStaffForShift = (shiftType: string, date: string) => {
    return schedule
      .filter((s: any) => s.shift_type.toLowerCase() === shiftType && s.shift_date.startsWith(date))
      .map((s: any) => s.staff_id);
  };

  // Listen to realtime updates from the hook
  useEffect(() => {
    if (jobStatus) {
      // Safely check status against our expected UI states
      if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
        setStatus(jobStatus.status);
      }
      
      let msg = jobStatus.message || jobStatus.error_message || '';
      if (typeof msg === 'object') {
          msg = msg.message || JSON.stringify(msg);
      }
      setMessage(msg);
    }
  }, [jobStatus]);

  const triggerSchedule = async () => {
    try {
      setStatus('queued');
      
      const daysInMonth = new Date(targetYear, targetMonth, 0).getDate();
      const payload = {
        month: targetMonth,
        year: targetYear,
        days_in_month: daysInMonth
      };

      // POST to the Phase 1 refactored synchronous-trigger endpoint
      const res = await fetch('http://localhost:5000/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
                ...payload
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
        <div style={{ marginBottom: '24px', display: 'flex', gap: '16px', justifyContent: 'center' }}>
          <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
            <label style={{ fontSize: '0.875rem', color: '#94a3b8', marginBottom: '4px' }}>Month (1-12)</label>
            <input 
              type="number" 
              min="1" max="12"
              value={targetMonth} 
              onChange={e => setTargetMonth(parseInt(e.target.value) || 1)}
              style={{ padding: '8px 12px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', width: '120px' }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
            <label style={{ fontSize: '0.875rem', color: '#94a3b8', marginBottom: '4px' }}>Year</label>
            <input 
              type="number" 
              value={targetYear} 
              onChange={e => setTargetYear(parseInt(e.target.value) || 2026)}
              style={{ padding: '8px 12px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', width: '120px' }}
            />
          </div>
        </div>

        <button 
          className="btn" 
          onClick={triggerSchedule}
          disabled={status === 'queued' || status === 'running'}
        >
          {(status === 'queued' || status === 'running') ? (
            <><span className="loading-spinner"></span> Optimizing...</>
          ) : (
            'Generate Monthly Schedule'
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

      {schedule.length > 0 ? (
        <div style={{ marginTop: '48px', width: '100%' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '24px', textAlign: 'center' }}>Generated Schedule Matrix</h2>
          <div className="table-container">
            <table className="schedule-table">
              <thead>
                <tr>
                  <th className="sticky-col" style={{ width: '150px' }}>Shift Period</th>
                  {uniqueDates.map(date => (
                    <th key={date} style={{ textAlign: 'center' }}>
                      {new Date(date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shiftTypes.map(shiftType => (
                  <tr key={shiftType}>
                    <td className="sticky-col">
                      <span className={`shift-badge badge-${shiftType}`}>
                        {shiftType.toUpperCase()}
                      </span>
                    </td>
                    {uniqueDates.map(date => {
                      const staffList = getStaffForShift(shiftType, date);
                      return (
                        <td key={date} style={{ textAlign: 'center', verticalAlign: 'top', padding: '12px 8px' }}>
                          {staffList.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'center' }}>
                              {staffList.map((staffId: string) => (
                                <span key={staffId} style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', background: 'rgba(255,255,255,0.08)', padding: '4px 8px', borderRadius: '4px', whiteSpace: 'nowrap' }}>
                                  {staffId}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span style={{ color: 'rgba(255,255,255,0.2)' }}>-</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div style={{ marginTop: '48px', width: '100%', textAlign: 'center', color: '#94a3b8' }}>
          <p style={{ fontSize: '1.125rem' }}>No schedule found for this month.</p>
          <p style={{ fontSize: '0.875rem', opacity: 0.7 }}>Click "Generate Monthly Schedule" to generate one!</p>
        </div>
      )}
    </main>
  );
}
