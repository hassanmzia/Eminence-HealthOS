import { useState } from "react";
import { register } from "../lib/authApi";

interface RegisterPageProps {
  onRegisterSuccess: () => void;
  onBackToLogin: () => void;
}

export function RegisterPage({ onRegisterSuccess, onBackToLogin }: RegisterPageProps) {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    password_confirm: "",
    first_name: "",
    last_name: "",
    phone: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validate passwords match
    if (formData.password !== formData.password_confirm) {
      setError("Passwords do not match");
      return;
    }

    // Validate password length
    if (formData.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setIsLoading(true);

    try {
      await register({
        email: formData.email,
        password: formData.password,
        password_confirm: formData.password_confirm,
        first_name: formData.first_name,
        last_name: formData.last_name,
        phone: formData.phone || undefined,
      });
      onRegisterSuccess();
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosError = err as { response?: { data?: { detail?: string; email?: string[]; password?: string[]; non_field_errors?: string[] } } };
        const errorData = axiosError.response?.data;
        if (errorData?.detail) {
          setError(errorData.detail);
        } else if (errorData?.email) {
          setError(`Email: ${errorData.email[0]}`);
        } else if (errorData?.password) {
          setError(`Password: ${errorData.password[0]}`);
        } else if (errorData?.non_field_errors) {
          setError(errorData.non_field_errors[0]);
        } else {
          setError("Registration failed. Please check your information.");
        }
      } else {
        setError("Registration failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const inputStyle = {
    width: "100%",
    padding: "12px 16px",
    border: "1px solid #d1d5db",
    borderRadius: 8,
    fontSize: 14,
    outline: "none",
    transition: "border-color 0.2s",
    boxSizing: "border-box" as const,
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
        maxWidth: 450,
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
            Create Account
          </h1>
          <p style={{ margin: "8px 0 0", color: "#6b7280", fontSize: 14 }}>
            Register for Health Platform
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

          {/* Name fields */}
          <div className="form-grid-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#374151" }}>
                First Name *
              </label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                required
                placeholder="John"
                style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = "#667eea"}
                onBlur={(e) => e.target.style.borderColor = "#d1d5db"}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#374151" }}>
                Last Name *
              </label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                required
                placeholder="Doe"
                style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = "#667eea"}
                onBlur={(e) => e.target.style.borderColor = "#d1d5db"}
              />
            </div>
          </div>

          {/* Email */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#374151" }}>
              Email *
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              placeholder="you@example.com"
              style={inputStyle}
              onFocus={(e) => e.target.style.borderColor = "#667eea"}
              onBlur={(e) => e.target.style.borderColor = "#d1d5db"}
            />
          </div>

          {/* Phone (optional) */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#374151" }}>
              Phone (optional)
            </label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="+1234567890"
              style={inputStyle}
              onFocus={(e) => e.target.style.borderColor = "#667eea"}
              onBlur={(e) => e.target.style.borderColor = "#d1d5db"}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#374151" }}>
              Password *
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              placeholder="At least 8 characters"
              minLength={8}
              style={inputStyle}
              onFocus={(e) => e.target.style.borderColor = "#667eea"}
              onBlur={(e) => e.target.style.borderColor = "#d1d5db"}
            />
          </div>

          {/* Confirm Password */}
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#374151" }}>
              Confirm Password *
            </label>
            <input
              type="password"
              value={formData.password_confirm}
              onChange={(e) => setFormData({ ...formData, password_confirm: e.target.value })}
              required
              placeholder="Confirm your password"
              minLength={8}
              style={inputStyle}
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
            {isLoading ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: "center" }}>
          <p style={{ fontSize: 14, color: "#6b7280" }}>
            Already have an account?{" "}
            <button
              onClick={onBackToLogin}
              style={{
                background: "none",
                border: "none",
                color: "#667eea",
                cursor: "pointer",
                fontWeight: 600,
                fontSize: 14,
              }}
            >
              Sign in
            </button>
          </p>
        </div>

        <div style={{ marginTop: 16, textAlign: "center" }}>
          <p style={{ fontSize: 11, color: "#9ca3af" }}>
            By registering, you agree to the Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
}
