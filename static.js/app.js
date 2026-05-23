const { useState, useEffect, useRef } = React;

// --- API Utility ---
const API_URL = '/api';

const apiRequest = async (endpoint, method, data) => {
    const meth = method || 'GET';
    const token = localStorage.getItem('token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const options = {
        method: meth,
        headers: headers,
        body: data ? JSON.stringify(data) : null
    };

    try {
        const response = await fetch(API_URL + endpoint, options);
        if (response.status === 401 && endpoint !== '/login') {
            localStorage.removeItem('token');
            localStorage.removeItem('teacher');
            window.location.reload();
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { message: 'Network error' };
    }
};

// --- Icons Helper ---
const Icon = ({ name, className }) => {
    const cls = className || '';
    useEffect(() => {
        if (window.lucide) window.lucide.createIcons();
    }, [name]);
    return <i data-lucide={name} className={cls}></i>;
};

// --- Components ---

const Sidebar = ({ activePage, setActivePage, teacher, onLogout }) => {
    const links = [
        { id: 'dashboard',     label: 'Dashboard',        icon: 'layout-dashboard' },
        { id: 'attendance',    label: 'Mark Attendance',   icon: 'check-square' },
        { id: 'students',      label: 'Student Database',  icon: 'users' },
        { id: 'notifications', label: 'Notification Log',  icon: 'bell' },
        { id: 'profile',       label: 'My Profile',        icon: 'user' },
    ];

    const teacherName = (teacher && teacher.name) || 'Teacher';
    const teacherDept = (teacher && teacher.department) || 'Department';

    return (
        <div className="w-64 h-screen glass-card rounded-none border-r border-t-0 border-b-0 border-l-0 p-6 flex flex-col fixed left-0 top-0">
            <div className="flex items-center gap-3 mb-10 px-2">
                <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                    <Icon name="graduation-cap" className="text-white" />
                </div>
                <h1 className="font-bold text-xl leading-tight">Smart<br/><span className="text-primary">Attendance</span></h1>
            </div>

            <nav className="flex-1">
                {links.map(link => (
                    <a
                        key={link.id}
                        href="#"
                        onClick={(e) => { e.preventDefault(); setActivePage(link.id); }}
                        className={'sidebar-link ' + (activePage === link.id ? 'active' : '')}
                    >
                        <Icon name={link.icon} />
                        <span>{link.label}</span>
                    </a>
                ))}
            </nav>

            <div className="mt-auto border-t border-glass-border pt-6">
                <div className="flex items-center gap-3 px-2 mb-4">
                    <div className="w-8 h-8 bg-pink-500 rounded-full flex items-center justify-center text-sm font-bold">
                        {teacherName.charAt(0)}
                    </div>
                    <div>
                        <p className="text-sm font-semibold">{teacherName}</p>
                        <p className="text-xs text-text-muted">{teacherDept}</p>
                    </div>
                </div>
                <button onClick={onLogout} className="sidebar-link w-full text-left text-red-400 hover:text-red-300">
                    <Icon name="log-out" />
                    <span>Logout</span>
                </button>
            </div>
        </div>
    );
};

// Fix #2: Remove hardcoded default credentials from login form
const LoginPage = ({ onLogin }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError]       = useState('');
    const [loading, setLoading]   = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        const res = await apiRequest('/login', 'POST', { username, password });
        setLoading(false);
        if (res && res.token) {
            onLogin(res);
        } else {
            setError(res.message || 'Login failed');
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-dark">
            <div className="max-w-md w-full glass-card p-10 animate-fade-in">
                <div className="text-center mb-10">
                    <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-6">
                        <Icon name="graduation-cap" className="text-white w-10 h-10" />
                    </div>
                    <h2 className="text-3xl font-bold mb-2">Welcome Back</h2>
                    <p className="text-text-muted">Smart Academic Monitoring System</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium mb-2">Username</label>
                        <input
                            type="text"
                            className="w-full glass-input"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            autoComplete="username"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-2">Password</label>
                        <input
                            type="password"
                            className="w-full glass-input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            autoComplete="current-password"
                        />
                    </div>
                    {error && <p className="text-red-400 text-sm">{error}</p>}
                    <button type="submit" disabled={loading} className="w-full btn-primary mt-4">
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>
            </div>
        </div>
    );
};

const Dashboard = () => {
    const [stats, setStats]           = useState(null);
    const [notifyStatus, setNotifyStatus] = useState({});  // Fix #8: track per-row notify state
    const chartRef      = useRef(null);
    // Fix #6: store chart instance ref so we can destroy it before re-creating
    const chartInstance = useRef(null);

    useEffect(() => {
        const loadStats = async () => {
            const data = await apiRequest('/analytics');
            if (data) setStats(data);
        };
        loadStats();
    }, []);

    useEffect(() => {
        if (stats && stats.subject_stats && chartRef.current && window.Chart) {
            // Fix #6: Destroy previous chart instance before creating a new one
            if (chartInstance.current) {
                chartInstance.current.destroy();
                chartInstance.current = null;
            }
            const ctx = chartRef.current.getContext('2d');
            chartInstance.current = new window.Chart(ctx, {
                type: 'bar',
                data: {
                    labels: stats.subject_stats.map(s => s.subject),
                    datasets: [{
                        label: 'Present Students',
                        data: stats.subject_stats.map(s => s.presents),
                        backgroundColor: '#6366f1',
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }
        // Cleanup on unmount
        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
                chartInstance.current = null;
            }
        };
    }, [stats]);

    // Fix #8: Functional notify parent handler
    const handleNotifyParent = async (roll) => {
        setNotifyStatus(prev => ({ ...prev, [roll]: 'loading' }));
        const res = await apiRequest('/notify_parent', 'POST', { roll_number: roll });
        if (res && res.message) {
            setNotifyStatus(prev => ({ ...prev, [roll]: 'sent' }));
        } else {
            setNotifyStatus(prev => ({ ...prev, [roll]: 'error' }));
        }
    };

    if (!stats) return <div className="p-10 text-white">Loading Analytics...</div>;

    return (
        <div className="animate-fade-in">
            <h2 className="text-3xl font-bold mb-8 text-white">Dashboard Overview</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
                <div className="glass-card stat-card border-l-4 border-primary">
                    <p className="text-text-muted text-sm uppercase tracking-wider">Total Students</p>
                    <p className="stat-value">{stats.total_students || 0}</p>
                </div>
                <div className="glass-card stat-card border-l-4 border-pink-500">
                    <p className="text-text-muted text-sm uppercase tracking-wider">Risky Students</p>
                    <p className="stat-value text-pink-400">{(stats.risky_students && stats.risky_students.length) || 0}</p>
                </div>
                {/* Fix #7: Display real avg_attendance from API instead of hardcoded 82% */}
                <div className="glass-card stat-card border-l-4 border-emerald-500">
                    <p className="text-text-muted text-sm uppercase tracking-wider">Avg Attendance</p>
                    <p className="stat-value text-emerald-400">
                        {stats.avg_attendance != null ? stats.avg_attendance + '%' : '—'}
                    </p>
                </div>
                <div className="glass-card stat-card border-l-4 border-amber-500">
                    <p className="text-text-muted text-sm uppercase tracking-wider">Alerts Sent</p>
                    <p className="stat-value text-amber-400">{stats.total_notifications || 0}</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 glass-card p-8">
                    <h3 className="text-xl font-semibold mb-6 text-white">Subject-wise Attendance</h3>
                    <div className="h-64">
                        <canvas ref={chartRef}></canvas>
                    </div>
                </div>
                <div className="glass-card p-8">
                    <h3 className="text-xl font-semibold mb-6 text-white">Most Absent</h3>
                    <div className="space-y-4">
                        {(stats.most_absent || []).map((s, i) => (
                            <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                                <span className="font-medium text-white">{s.name}</span>
                                <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm font-bold">{s.count} Misses</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="mt-8 glass-card p-8">
                <h3 className="text-xl font-semibold mb-6 text-white">Critical Risk Watchlist</h3>
                <div className="table-container">
                    <table className="text-white">
                        <thead>
                            <tr>
                                <th className="text-left p-4">Name</th>
                                <th className="text-left p-4">Roll Number</th>
                                <th className="text-left p-4">Attendance %</th>
                                <th className="text-left p-4">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(stats.risky_students || []).map((s, i) => (
                                <tr key={i}>
                                    <td className="p-4">{s.name}</td>
                                    <td className="p-4">{s.roll}</td>
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-full bg-white/10 rounded-full h-2 max-w-[100px]">
                                                <div className="bg-red-500 h-2 rounded-full" style={{width: s.percentage + '%'}}></div>
                                            </div>
                                            <span className="text-red-400 font-bold">{s.percentage}%</span>
                                        </div>
                                    </td>
                                    {/* Fix #8: Wired up with real API call and loading/sent states */}
                                    <td className="p-4">
                                        {notifyStatus[s.roll] === 'sent' ? (
                                            <span className="text-emerald-400 text-sm">✓ Notified</span>
                                        ) : (
                                            <button
                                                onClick={() => handleNotifyParent(s.roll)}
                                                disabled={notifyStatus[s.roll] === 'loading'}
                                                className="text-primary hover:underline disabled:opacity-50"
                                            >
                                                {notifyStatus[s.roll] === 'loading' ? 'Sending...' : 'Notify Parent'}
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

const AttendanceForm = () => {
    const [formData, setFormData] = useState({
        subject: 'Database Management Systems',
        lecture_number: 1,
        date: new Date().toISOString().split('T')[0],
        absent_rolls: ''
    });
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError]     = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setSuccess(null);
        const res = await apiRequest('/attendance', 'POST', formData);
        setLoading(false);
        if (res && res.message && !res.message.toLowerCase().includes('error') && !res.message.toLowerCase().includes('required') && !res.message.toLowerCase().includes('invalid')) {
            setSuccess(res);
            // Fix #15: Don't clear absent_rolls so teacher can review what was submitted
            setTimeout(() => setSuccess(null), 6000);
        } else {
            setError(res.message || 'Submission failed');
        }
    };

    return (
        <div className="animate-fade-in max-w-4xl text-white">
            <h2 className="text-3xl font-bold mb-8">Mark New Attendance</h2>

            <div className="glass-card p-8">
                <form onSubmit={handleSubmit} className="space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                            <label className="block text-sm font-medium mb-2 text-text-muted">Subject</label>
                            <select
                                className="w-full glass-input"
                                value={formData.subject}
                                onChange={(e) => setFormData({...formData, subject: e.target.value})}
                            >
                                <option>Database Management Systems</option>
                                <option>Data Structures</option>
                                <option>Machine Learning</option>
                                <option>Cloud Computing</option>
                                <option>Software Engineering</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2 text-text-muted">Lecture Number</label>
                            <input
                                type="number"
                                className="w-full glass-input"
                                value={formData.lecture_number}
                                onChange={(e) => setFormData({...formData, lecture_number: e.target.value})}
                                min="1" max="8"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2 text-text-muted">Date</label>
                            <input
                                type="date"
                                className="w-full glass-input"
                                value={formData.date}
                                onChange={(e) => setFormData({...formData, date: e.target.value})}
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2 text-text-muted">
                            Absent Roll Numbers{' '}
                            {/* Fix #15: Remove `required` — all-present is a valid submission */}
                            <span className="text-xs italic">(Comma-separated, e.g. 101, 105 — leave blank if all present)</span>
                        </label>
                        <textarea
                            className="w-full glass-input h-32"
                            placeholder="Example: 102, 108, 125... (or leave blank if everyone is present)"
                            value={formData.absent_rolls}
                            onChange={(e) => setFormData({...formData, absent_rolls: e.target.value})}
                        ></textarea>
                    </div>

                    {error && <p className="text-red-400 text-sm">{error}</p>}

                    <div className="flex items-center gap-6">
                        <button type="submit" disabled={loading} className="btn-primary min-w-[200px]">
                            {loading ? 'Processing...' : 'Submit Attendance'}
                        </button>
                        {success && (
                            <div className="text-emerald-400 flex items-center gap-2">
                                <Icon name="check-circle" />
                                <span>{success.message}! {(success.notifications && success.notifications.length) || 0} Parent Alerts Sent.</span>
                            </div>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
};

const StudentList = () => {
    const [students, setStudents] = useState([]);
    const [search, setSearch]     = useState('');

    useEffect(() => {
        const load = async () => {
            const data = await apiRequest('/students');
            if (data && Array.isArray(data)) setStudents(data);
        };
        load();
    }, []);

    const filtered = students.filter(s =>
        (s.name || '').toLowerCase().includes(search.toLowerCase()) ||
        (s.roll_number || '').includes(search)
    );

    return (
        <div className="animate-fade-in text-white">
            <div className="flex justify-between items-center mb-8">
                <h2 className="text-3xl font-bold">Student Database</h2>
                <div className="relative">
                    <Icon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted w-4 h-4" />
                    <input
                        type="text"
                        placeholder="Search by name or roll..."
                        className="glass-input pl-10 w-80"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
            </div>

            <div className="glass-card p-6">
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th className="text-left p-4">Roll No</th>
                                <th className="text-left p-4">Full Name</th>
                                <th className="text-left p-4">Department</th>
                                <th className="text-left p-4">Semester</th>
                                <th className="text-left p-4">Parent Contact</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map(s => (
                                <tr key={s.id}>
                                    <td className="p-4 font-bold text-primary">{s.roll_number}</td>
                                    <td className="p-4">{s.name}</td>
                                    <td className="p-4">{s.department}</td>
                                    <td className="p-4">Sem {s.semester}</td>
                                    <td className="p-4">{s.parent_mobile}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

const NotificationLog = () => {
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        const load = async () => {
            const data = await apiRequest('/notifications');
            if (data && Array.isArray(data)) setLogs(data);
        };
        load();
    }, []);

    const getTypeColor = (type) => {
        if (type === 'Alert' || type === 'Manual Alert') return 'bg-blue-500/20 text-blue-400';
        if (type === 'Critical')        return 'bg-red-500/20 text-red-400';
        if (type === 'Low Attendance')  return 'bg-pink-500/20 text-pink-400';
        return 'bg-amber-500/20 text-amber-400';
    };

    return (
        <div className="animate-fade-in text-white">
            <h2 className="text-3xl font-bold mb-8">Parent Notification History</h2>
            <div className="space-y-4">
                {logs.map(log => (
                    <div key={log.id} className="glass-card p-6 flex gap-6 items-start">
                        <div className={'shrink-0 w-12 h-12 rounded-xl flex items-center justify-center ' + getTypeColor(log.type)}>
                            <Icon name={log.type === 'Alert' || log.type === 'Manual Alert' ? 'message-square' : 'alert-triangle'} />
                        </div>
                        <div className="flex-1">
                            <div className="flex justify-between items-center mb-1">
                                <span className="font-bold">{log.student_name} <span className="text-text-muted text-sm font-normal">({log.roll_number})</span></span>
                                <span className="text-xs text-text-muted">{log.date}</span>
                            </div>
                            <p className="text-text-muted text-sm mb-3">{log.message}</p>
                            <span className={'text-[10px] uppercase tracking-widest font-bold px-2 py-1 rounded-md ' + getTypeColor(log.type)}>
                                {log.type} Sent
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// --- App Orchestrator ---

const App = () => {
    const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('token'));
    const [teacher, setTeacher]       = useState(null);
    const [activePage, setActivePage] = useState('dashboard');

    useEffect(() => {
        const tStr = localStorage.getItem('teacher');
        if (tStr) {
            try { setTeacher(JSON.parse(tStr)); }
            catch(e) { console.error('Failed to parse teacher data'); }
        }
    }, []);

    const handleLogin = (data) => {
        localStorage.setItem('token', data.token);
        localStorage.setItem('teacher', JSON.stringify(data.teacher));
        setTeacher(data.teacher);
        setIsLoggedIn(true);
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('teacher');
        setIsLoggedIn(false);
        setTeacher(null);
    };

    if (!isLoggedIn) return <LoginPage onLogin={handleLogin} />;

    const renderPage = () => {
        if (activePage === 'dashboard')     return <Dashboard />;
        if (activePage === 'attendance')    return <AttendanceForm />;
        if (activePage === 'students')      return <StudentList />;
        if (activePage === 'notifications') return <NotificationLog />;
        if (activePage === 'profile') {
            // Fix #13: Pull real data from teacher object, not hardcoded strings
            const tName = (teacher && teacher.name) || 'Teacher';
            const tDept = (teacher && teacher.department) || 'Department';
            const tUser = (teacher && teacher.username) || '—';
            const tId   = (teacher && teacher.id) ? 'TCH-' + String(teacher.id).padStart(4, '0') : '—';
            return (
                <div className="glass-card p-10 max-w-2xl mx-auto text-center text-white">
                    <div className="w-32 h-32 bg-primary/20 rounded-full flex items-center justify-center mx-auto mb-6 text-5xl font-bold text-primary">
                        {tName.charAt(0)}
                    </div>
                    <h2 className="text-3xl font-bold mb-2">{tName}</h2>
                    <p className="text-text-muted mb-8">{tDept} | Senior Professor</p>
                    <div className="grid grid-cols-2 gap-4 text-left">
                        <div className="p-4 bg-white/5 rounded-xl border border-glass-border">
                            <p className="text-xs text-text-muted uppercase">Employee ID</p>
                            <p className="font-semibold">{tId}</p>
                        </div>
                        <div className="p-4 bg-white/5 rounded-xl border border-glass-border">
                            <p className="text-xs text-text-muted uppercase">Username</p>
                            <p className="font-semibold">{tUser}</p>
                        </div>
                    </div>
                </div>
            );
        }
        return <Dashboard />;
    };

    return (
        <div className="flex min-h-screen bg-dark">
            <Sidebar
                activePage={activePage}
                setActivePage={setActivePage}
                teacher={teacher}
                onLogout={handleLogout}
            />
            <main className="flex-1 ml-64 p-10">
                <div className="max-w-7xl mx-auto">
                    {renderPage()}
                </div>
            </main>
        </div>
    );
};

const renderApp = () => {
    const rootElement = document.getElementById('root');
    if (rootElement && window.ReactDOM) {
        const root = window.ReactDOM.createRoot(rootElement);
        root.render(<App />);
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderApp);
} else {
    renderApp();
}
