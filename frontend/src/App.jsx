import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import RegisterPage from './pages/RegisterPage'
import VerifyPage from './pages/VerifyPage'
import HistoryPage from './pages/HistoryPage'
import './App.css'

function App() {
    return (
        <Router>
            <div className="app">
                <nav className="navbar">
                    <div className="nav-brand">
                        <span className="logo">⬡</span>
                        <span className="brand-name">DID++</span>
                    </div>
                    <div className="nav-links">
                        <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                            Register
                        </NavLink>
                        <NavLink to="/verify" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                            Verify
                        </NavLink>
                        <NavLink to="/history" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                            History
                        </NavLink>
                    </div>
                </nav>

                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<RegisterPage />} />
                        <Route path="/verify" element={<VerifyPage />} />
                        <Route path="/history" element={<HistoryPage />} />
                    </Routes>
                </main>

                <footer className="footer">
                    <p>DID++ Biometric Identity System • Secured by Ethereum</p>
                </footer>
            </div>
        </Router>
    )
}

export default App
