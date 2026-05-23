console.log('App.js is loading...');
const { useState } = React;

const App = () => {
    return (
        <div className="min-h-screen flex items-center justify-center bg-dark text-white p-10">
            <div className="glass-card p-10 text-center">
                <h1 className="text-4xl font-bold mb-4">Smart Attendance System</h1>
                <p className="text-text-muted mb-6">If you see this, React is working!</p>
                <button className="btn-primary" onClick={() => alert('Button Clicked!')}>
                    Test Interaction
                </button>
            </div>
        </div>
    );
};

const renderApp = () => {
    console.log('Mounting React...');
    const rootElement = document.getElementById('root');
    if (rootElement) {
        const root = ReactDOM.createRoot(rootElement);
        root.render(<App />);
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderApp);
} else {
    renderApp();
}
