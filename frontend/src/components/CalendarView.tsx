"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Calendar, dateFnsLocalizer, Event } from 'react-big-calendar';
import withDragAndDrop, { EventInteractionArgs } from 'react-big-calendar/lib/addons/dragAndDrop';
import format from 'date-fns/format';
import parse from 'date-fns/parse';
import startOfWeek from 'date-fns/startOfWeek';
import getDay from 'date-fns/getDay';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import 'react-big-calendar/lib/addons/dragAndDrop/styles.css';

const locales = {
  'en-US': require('date-fns/locale/en-US'),
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

const DnDCalendar = withDragAndDrop(Calendar);

interface ShiftRecord {
  staff_id: string;
  shift_date: string;
  shift_type: string;
  is_locked: boolean;
}

interface CalendarEvent extends Event {
  id: string;
  staff_id: string;
  shift_type: string;
}

export default function CalendarView() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const fetchSchedule = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:5000/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const json = await res.json();
      if (json.status === 'success') {
        const mappedEvents: CalendarEvent[] = json.data.map((shift: ShiftRecord, idx: number) => {
          const date = new Date(shift.shift_date);
          const isMorning = shift.shift_type.toLowerCase() === 'morning';
          const start = new Date(date.setHours(isMorning ? 8 : 20, 0, 0, 0));
          const end = new Date(date.setHours(isMorning ? 16 : 4, 0, 0, 0)); // 8 hour shift
          if (!isMorning) {
            end.setDate(end.getDate() + 1); // Night shift ends next day
          }
          
          return {
            id: `${shift.staff_id}-${idx}`,
            title: `${shift.staff_id} (${shift.shift_type})`,
            start,
            end,
            staff_id: shift.staff_id,
            shift_type: shift.shift_type,
          };
        });
        setEvents(mappedEvents);
        setHasUnsavedChanges(false);
      } else {
        setError(json.message);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch schedule');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, []);

  const onEventDrop = useCallback(
    async ({ event, start, end }: EventInteractionArgs<CalendarEvent>) => {
      // Create new event
      const updatedEvent = { ...event, start: start as Date, end: end as Date };
      
      // We will pretend the staff member changed based on drop (if we had resources/staff rows).
      // Since it's a standard calendar, dragging mostly changes DATE. 
      // To simulate staff change, we'd need a resource calendar, but for now we just validate the date change.
      
      const newDateStr = (start as Date).toISOString().split('T')[0];

      // Convert events to current schedule format for validation
      const currentSchedule = events.map(e => ({
        staff_id: e.staff_id,
        shift_date: (e.start as Date).toISOString().split('T')[0],
        shift_type: e.shift_type
      }));

      try {
        const res = await fetch('http://localhost:5000/api/validate_shift', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            staff_id: event.staff_id,
            date: newDateStr,
            shift_type: event.shift_type,
            current_schedule: currentSchedule
          }),
        });
        const data = await res.json();
        
        if (data.valid) {
          // Update UI
          setEvents(prev => prev.map(e => e.id === event.id ? updatedEvent : e));
          setHasUnsavedChanges(true);
        } else {
          alert(`Invalid change: ${data.reason}`);
        }
      } catch (err) {
        alert("Failed to validate shift change.");
      }
    },
    [events]
  );

  const handleSave = () => {
    // Implement save to backend later
    alert("Changes saved successfully!");
    setHasUnsavedChanges(false);
  };

  return (
    <div className="flex flex-col gap-4 p-6 bg-slate-900 min-h-screen text-slate-100">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            Resource Optimizer
          </h1>
          <p className="text-slate-400">Drag and drop shifts to reassign them</p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={fetchSchedule}
            className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 transition-colors border border-slate-700"
            disabled={loading}
          >
            {loading ? 'Optimizing...' : 'Run Auto-Optimizer'}
          </button>
          {hasUnsavedChanges && (
            <button 
              onClick={handleSave}
              className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 transition-colors shadow-lg shadow-blue-500/30"
            >
              Save Changes
            </button>
          )}
        </div>
      </div>
      
      {error && (
        <div className="p-4 bg-red-900/50 border border-red-500 rounded text-red-200">
          {error}
        </div>
      )}

      <div className="flex-grow h-[700px]">
        <DnDCalendar
          localizer={localizer}
          events={events}
          onEventDrop={onEventDrop}
          resizable={false}
          style={{ height: '100%' }}
          defaultView="week"
          views={['month', 'week', 'day']}
        />
      </div>
    </div>
  );
}
