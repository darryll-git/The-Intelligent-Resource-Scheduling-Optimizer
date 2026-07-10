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

export const useScheduleSubscription = (jobId: string | null) => {
  const [schedule, setSchedule] = useState<Shift[]>([]);
  const [jobStatus, setJobStatus] = useState<SolverLog | null>(null);

  // Fetch initial schedule on mount
  useEffect(() => {
    const fetchInitial = async () => {
      const { data } = await supabase
        .from('fact_shifts')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(14);
        
      if (data) setSchedule(data as Shift[]);
    };
    if (supabaseUrl && supabaseKey) {
        fetchInitial();
    }
  }, []);

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
          setSchedule((prev) => [payload.new as Shift, ...prev].slice(0, 14));
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
