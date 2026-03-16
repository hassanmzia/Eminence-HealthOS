import { useState } from "react";
import { useAuth } from "../context/AuthContext";

interface LoginPageProps {
  onLoginSuccess: () => void;
  onRegister?: () => void;
}

export function LoginPage({ onLoginSuccess, onRegister }: LoginPageProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(email, password);
      onLoginSuccess();
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosError = err as { response?: { data?: { detail?: string; non_field_errors?: string[] } } };
        const errorData = axiosError.response?.data;
        if (errorData?.detail) {
          setError(errorData.detail);
        } else if (errorData?.non_field_errors) {
          setError(errorData.non_field_errors[0]);
        } else {
          setError("Invalid email or password");
        }
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
    }}>
      <div className="login-card" style={{
        background: "white",
        borderRadius: 16,
        padding: 40,
        width: "100%",
        maxWidth: 400,
        boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
      }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{
            width: 64,
            height: 64,
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            borderRadius: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 16px",
          }}>
            <span style={{ fontSize: 32, color: "white" }}>+</span>
          </div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#1f2937" }}>
            Health Platform
          </h1>
          <p style={{ margin: "8px 0 0", color: "#6b7280", fontSize: 14 }}>
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && (
            <div style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: 8,
              padding: 12,
              marginBottom: 16,
              color: "#dc2626",
              fontSize: 14,
            }}>
              {error}
            </div>
          )}

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#374151" }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              style={{
                width: "100%",
                padding: "12px 16px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                outline: "none",
                transition: "border-color 0.2s",
                boxSizing: "border-box",
              }}
              onFocus={(e) => e.target.style.borderColor = "#667eea"}
              onBlur={(e) => e.target.style.borderColor = "#d1d5db"}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#374151" }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter your password"
              style={{
                width: "100%",
                padding: "12px 16px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                outline: "none",
                transition: "border-color 0.2s",
                boxSizing: "border-box",
              }}
              onFocus={(e) => e.target.style.borderColor = "#667eea"}
              onBlur={(e) => e.target.style.borderColor = "#d1d5db"}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: "100%",
              padding: "12px 16px",
              background: isLoading ? "#9ca3af" : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              color: "white",
              border: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: isLoading ? "not-allowed" : "pointer",
              transition: "transform 0.2s, box-shadow 0.2s",
            }}
            onMouseOver={(e) => !isLoading && (e.currentTarget.style.transform = "translateY(-1px)")}
            onMouseOut={(e) => (e.currentTarget.style.transform = "translateY(0)")}
          >
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        {onRegister && (
          <div style={{ marginTop: 24, textAlign: "center" }}>
            <p style={{ fontSize: 14, color: "#6b7280" }}>
              Don't have an account?{" "}
              <button
                onClick={onRegister}
                style={{
                  background: "none",
                  border: "none",
                  color: "#667eea",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Create account
              </button>
            </p>
          </div>
        )}

        <div style={{ marginTop: 16, textAlign: "center" }}>
          <p style={{ fontSize: 12, color: "#9ca3af" }}>
            Demo credentials: admin@health.local / admin123
          </p>
        </div>
      </div>
    </div>
  );
}
