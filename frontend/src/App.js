import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import JobsList from "./Pages/JobsList";
import AddEditJob from "./Pages/AddEditJob";
import ToastProvider from "./Components/ToastProvider";
import "./App.css";

function Nav() {
  const nav = useNavigate();
  return (
    <header className="nav">
      <div className="brand" onClick={() => nav("/")}>Bitbash Jobs</div>
      <nav>
        <Link to="/">Jobs</Link>
        <Link to="/add">Add Job</Link>
      </nav>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Nav />
        <main className="container">
          <Routes>
            <Route path="/" element={<JobsList />} />
            <Route path="/add" element={<AddEditJob mode="add" />} />
            <Route path="/edit/:id" element={<AddEditJob mode="edit" />} />
          </Routes>
        </main>
        <footer className="footer">© {new Date().getFullYear()} Bitbash</footer>
      </ToastProvider>
    </BrowserRouter>
  );
}
