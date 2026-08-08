document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const apiKeyInput = document.getElementById('apiKey');
    const apiUrlInput = document.getElementById('apiUrl');
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    
    const generateBtn = document.getElementById('generateBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const statusMessage = document.getElementById('statusMessage');
    
    const scheduleGrid = document.getElementById('scheduleGrid');
    const scheduleLoading = document.getElementById('scheduleLoading');
    const emptyState = document.getElementById('emptyState');
    
    const statTotalShifts = document.getElementById('statTotalShifts');
    const statStaffCount = document.getElementById('statStaffCount');

    // Load saved config
    const savedApiKey = localStorage.getItem('irso_api_key');
    const savedApiUrl = localStorage.getItem('irso_api_url');
    
    if (savedApiKey) apiKeyInput.value = savedApiKey;
    if (savedApiUrl) apiUrlInput.value = savedApiUrl;

    // Save config
    saveConfigBtn.addEventListener('click', () => {
        localStorage.setItem('irso_api_key', apiKeyInput.value.trim());
        localStorage.setItem('irso_api_url', apiUrlInput.value.trim());
        showStatus('Configuration saved!', 'success');
        fetchSchedule(); // Refresh automatically on save
    });

    // Generate Schedule
    generateBtn.addEventListener('click', async () => {
        const apiKey = apiKeyInput.value.trim();
        const apiUrl = apiUrlInput.value.trim();
        
        if (!apiKey) {
            showStatus('Please enter an API Key first', 'error');
            return;
        }

        generateBtn.classList.add('loading');
        generateBtn.disabled = true;

        try {
            const response = await fetch(`${apiUrl}/api/schedule`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': apiKey
                },
                body: JSON.stringify({
                    // Dynamic Webhook handled by API (now defaults to None)
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                showStatus(`Generation started! Job ID: ${data.job_id}. This takes ~10 seconds.`, 'success');
                // Poll for completion after 10 seconds (for this demo, we'll just wait and refresh)
                setTimeout(() => fetchSchedule(), 12000);
            } else {
                showStatus(data.message || data.error || 'Failed to trigger schedule', 'error');
            }
        } catch (err) {
            showStatus(`Connection error: ${err.message}`, 'error');
        } finally {
            generateBtn.classList.remove('loading');
            generateBtn.disabled = false;
        }
    });

    // Refresh Data
    refreshBtn.addEventListener('click', fetchSchedule);

    // Fetch and render Schedule
    async function fetchSchedule() {
        const apiKey = apiKeyInput.value.trim();
        const apiUrl = apiUrlInput.value.trim();

        if (!apiKey) return;

        scheduleGrid.classList.add('hidden');
        emptyState.classList.add('hidden');
        scheduleLoading.classList.remove('hidden');

        try {
            const response = await fetch(`${apiUrl}/api/shifts`, {
                headers: { 'X-API-Key': apiKey }
            });

            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized - Check API Key');
                throw new Error('Failed to fetch schedule data');
            }

            const shifts = await response.json();
            
            if (!shifts || shifts.length === 0) {
                scheduleLoading.classList.add('hidden');
                emptyState.classList.remove('hidden');
                statTotalShifts.textContent = '0';
                statStaffCount.textContent = '0';
                return;
            }

            renderSchedule(shifts);
            showStatus('Schedule refreshed', 'success');

        } catch (err) {
            scheduleLoading.classList.add('hidden');
            emptyState.classList.remove('hidden');
            showStatus(`Error: ${err.message}`, 'error');
        }
    }

    function renderSchedule(shifts) {
        // Clear grid
        scheduleGrid.innerHTML = '';
        
        // Render headers (Mon-Sun for simplicity, assuming start date is known)
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        days.forEach(day => {
            const div = document.createElement('div');
            div.className = 'grid-header';
            div.textContent = day;
            scheduleGrid.appendChild(div);
        });

        // Group shifts by date
        const shiftsByDate = {};
        const uniqueStaff = new Set();
        
        shifts.forEach(shift => {
            uniqueStaff.add(shift.staff_id);
            const dateStr = shift.shift_date.split('T')[0];
            if (!shiftsByDate[dateStr]) shiftsByDate[dateStr] = [];
            shiftsByDate[dateStr].push(shift);
        });

        // Sort dates to create a sequential grid
        const sortedDates = Object.keys(shiftsByDate).sort();
        
        sortedDates.forEach(dateStr => {
            const dateObj = new Date(dateStr);
            const dayCell = document.createElement('div');
            dayCell.className = 'day-cell';
            
            const dateLabel = document.createElement('div');
            dateLabel.className = 'date-label';
            dateLabel.textContent = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
            dayCell.appendChild(dateLabel);

            // Add shifts
            const dayShifts = shiftsByDate[dateStr];
            dayShifts.forEach(shift => {
                const shiftBlock = document.createElement('div');
                shiftBlock.className = `shift-block ${shift.shift_type.toLowerCase()}`;
                
                const nameSpan = document.createElement('span');
                nameSpan.className = 'staff-name';
                nameSpan.textContent = shift.staff_id; // If we had dim_staff we'd use real names

                const typeSpan = document.createElement('span');
                typeSpan.className = 'shift-type-badge';
                typeSpan.textContent = shift.shift_type.charAt(0).toUpperCase();

                shiftBlock.appendChild(nameSpan);
                shiftBlock.appendChild(typeSpan);
                dayCell.appendChild(shiftBlock);
            });

            scheduleGrid.appendChild(dayCell);
        });

        // Update stats
        statTotalShifts.textContent = shifts.length;
        statStaffCount.textContent = uniqueStaff.size;

        scheduleLoading.classList.add('hidden');
        scheduleGrid.classList.remove('hidden');
    }

    function showStatus(msg, type) {
        statusMessage.textContent = msg;
        statusMessage.className = `status-message ${type === 'error' ? 'error' : ''}`;
        statusMessage.style.display = 'block';
        
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 5000);
    }

    // Initial load attempt if key is present
    if (savedApiKey) {
        fetchSchedule();
    }
});
