import { useState, useEffect } from 'react'
import './App.css'

interface ShiftRecord {
  staff_id: string;
  shift_date: string;
  shift_type: string;
  is_locked: boolean;
}

function App() {
  const [schedule, setSchedule] = useState<ShiftRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/schedule.json')
      .then(res => {
        if (!res.ok) throw new Error('Schedule not found. Run the optimizer first!');
        return res.json();
      })
      .then(data => {
        setSchedule(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const totalShifts = schedule.length;
  const uniqueStaff = new Set(schedule.map(s => s.staff_id)).size;
  const startDate = schedule.length > 0 ? new Date(schedule[0].shift_date).toLocaleDateString() : 'N/A';
  const endDate = schedule.length > 0 ? new Date(schedule[schedule.length - 1].shift_date).toLocaleDateString() : 'N/A';

  return (
    <div className="dashboard">
      <header className="header">
        <div>
          <h1>Intelligent Scheduler</h1>
          <p style={{ color: '#94a3b8', marginTop: '0.5rem' }}>AI-Enhanced Resource Optimization Engine</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="shift-badge shift-morning" style={{ fontSize: '0.875rem' }}>Local Mode Active</div>
        </div>
      </header>

      <section className="stats">
        <div className="stat-card">
          <div className="stat-label">Total Assignments</div>
          <div className="stat-value">{totalShifts}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Staff</div>
          <div className="stat-value">{uniqueStaff}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Period</div>
          <div className="stat-value" style={{ fontSize: '1rem' }}>{startDate} - {endDate}</div>
        </div>
      </section>

      <main className="schedule-container">
        {loading ? (
          <div style={{ padding: '4rem', textAlign: 'center', color: '#94a3b8' }}>Loading schedule...</div>
        ) : error ? (
          <div style={{ padding: '4rem', textAlign: 'center', color: '#ef4444' }}>
            <p>❌ {error}</p>
            <p style={{ fontSize: '0.875rem', marginTop: '1rem' }}>Run <code>python engine/solver.py --local</code> to generate it.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Staff ID</th>
                <th>Shift Type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {schedule.map((shift, idx) => (
                <tr key={idx}>
                  <td>
                    <div className="date-text">{new Date(shift.shift_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
                  </td>
                  <td>
                    <span className="staff-id">{shift.staff_id}</span>
                  </td>
                  <td>
                    <span className={`shift-badge ${shift.shift_type === 'Morning' ? 'shift-morning' : 'shift-night'}`}>
                      {shift.shift_type}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: '#10b981', fontSize: '0.875rem' }}>● Optimized</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
      
      <footer style={{ textAlign: 'center', color: '#475569', fontSize: '0.75rem', marginTop: '2rem' }}>
        &copy; 2024 Intelligent Resource & Scheduling Optimizer. Powered by Google OR-Tools.
      </footer>
    </div>
  )
}

export default App
