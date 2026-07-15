import { useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
const supabase = createClient(supabaseUrl, supabaseKey);

export type Shift = {
  staff_id: string;
  shift_date: string;
  shift_type: string;
  is_locked: boolean;
};

export type SolverLog = {
  job_id: string;
  status: 'completed' | 'failed';
  message?: string;
  error_message?: string;
};

export const useScheduleSubscription = (jobId: string | null, targetMonth: number, targetYear: number) => {
  const [schedule, setSchedule] = useState<Shift[]>([]);
  const [jobStatus, setJobStatus] = useState<SolverLog | null>(null);

  // Fetch initial schedule on mount and when month/year changes
  useEffect(() => {
    const fetchInitial = async () => {
      const startDateStr = `${targetYear}-${String(targetMonth).padStart(2, '0')}-01`;
      const daysInMonth = new Date(targetYear, targetMonth, 0).getDate();
      const endDateStr = `${targetYear}-${String(targetMonth).padStart(2, '0')}-${daysInMonth}`;

      const { data } = await supabase
        .from('fact_shifts')
        .select('*')
        .gte('shift_date', startDateStr)
        .lte('shift_date', endDateStr)
        .order('shift_date', { ascending: true })
        .limit(1000);
        
      if (data) setSchedule(data as Shift[]);
    };
    if (supabaseUrl && supabaseKey) {
        fetchInitial();
    }
  }, [targetMonth, targetYear]);

  useEffect(() => {
    if (!supabaseUrl || !supabaseKey) return;

    // Subscribe to solver_logs to instantly catch orchestrator success/failure
    const logsSubscription = supabase
      .channel('solver-logs-channel')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'solver_logs' },
        (payload) => {
          let newLog: SolverLog | null = null;
          
          // Handle legacy schema where n8n logs are dumped into log_text as JSON
          if (payload.new.log_text) {
              try {
                  const parsed = JSON.parse(payload.new.log_text);
                  if (parsed.job_id) {
                      newLog = parsed;
                  }
              } catch (e) {
                  // Ignore non-json log_text
              }
          }
          
          if (!newLog) {
              newLog = payload.new as SolverLog;
          }

          // If a job is running and we just got a log for it
          if (jobId && newLog.job_id === jobId) {
            setJobStatus(newLog);
          } else if (!jobId) {
            // Update anyway if no specific job tracking
            setJobStatus(newLog);
          }
        }
      )
      .subscribe();

    // Subscribe to fact_shifts to instantly append new schedule to the UI
    const shiftsSubscription = supabase
      .channel('fact-shifts-channel')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'fact_shifts' },
        (payload) => {
          // Instantly mutate state with the new shift (React state triggers re-render)
          setSchedule((prev) => [payload.new as Shift, ...prev].slice(0, 1000));
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(logsSubscription);
      supabase.removeChannel(shiftsSubscription);
    };
  }, [jobId]);

  return { schedule, jobStatus, setSchedule };
};
