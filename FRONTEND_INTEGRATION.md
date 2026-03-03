# Frontend Integration Guide - Email System

## 📧 New API Endpoints

Your frontend needs to integrate with these new endpoints:

---

## 1. Email Verification

### Endpoint: `POST /api/auth/verify-email/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "verification_token_from_url"
}
```

**Response (Success):**
```json
{
  "message": "Email verified successfully!"
}
```

**Frontend Flow:**
1. User clicks verification link in email: `http://localhost:3000/verify-email/{token}`
2. Extract token from URL params
3. If user is logged in, call endpoint with token
4. Show success message
5. Redirect to dashboard or profile

**Example (React/TypeScript):**
```typescript
// In verify-email page component
const { token } = useParams();

const handleVerify = async () => {
  try {
    await api.post('/api/auth/verify-email/', { token });
    toast.success('Email verified successfully!');
    navigate('/dashboard');
  } catch (error) {
    toast.error('Verification failed. Please try again.');
  }
};
```

---

## 2. Password Reset Request

### Endpoint: `POST /api/auth/request-password-reset/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If the email exists, a password reset link has been sent."
}
```

**Frontend Flow:**
1. User enters email in "Forgot Password" form
2. Call this endpoint
3. Always show success message (security - don't reveal if email exists)
4. Tell user to check their email

**Example (React/TypeScript):**
```typescript
const handlePasswordReset = async (email: string) => {
  try {
    const response = await api.post('/api/auth/request-password-reset/', { 
      email 
    });
    toast.success(response.data.message);
    setShowConfirmation(true);
  } catch (error) {
    toast.error('Something went wrong. Please try again.');
  }
};
```

---

## 3. Password Reset Confirm

### Endpoint: `POST /api/auth/confirm-password-reset/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "reset_token_from_url",
  "new_password": "NewSecurePassword123!"
}
```

**Response:**
```json
{
  "message": "Password has been reset successfully."
}
```

**Frontend Flow:**
1. User clicks reset link in email: `http://localhost:3000/reset-password/{token}`
2. Show password reset form with new password fields
3. Call endpoint with token and new password
4. On success, redirect to login page

**Example (React/TypeScript):**
```typescript
interface ResetForm {
  new_password: string;
  confirm_password: string;
}

const handleResetConfirm = async (data: ResetForm) => {
  try {
    await api.post('/api/auth/confirm-password-reset/', {
      token, // from URL params
      new_password: data.new_password
    });
    toast.success('Password reset successfully!');
    navigate('/login');
  } catch (error) {
    toast.error('Invalid or expired token');
  }
};
```

---

## 4. Registration (Updated)

### Endpoint: `POST /api/auth/register/`

**No changes to API**, but now it automatically:
- Sends verification email
- Sets user as unverified until they click link

**Frontend Changes:**
After registration, show message:
```
✅ Registration successful!
📧 Please check your email to verify your account.
```

**Example:**
```typescript
const handleRegister = async (userData: RegisterData) => {
  try {
    const response = await api.post('/api/auth/register/', userData);
    // Login user or show verification message
    toast.info('Please check your email to verify your account');
    navigate('/verify-email-sent');
  } catch (error) {
    toast.error('Registration failed');
  }
};
```

---

## 🔧 Updated API Client

Add these methods to your API client (`src/lib/api.ts` or similar):

```typescript
class ApiService {
  // ... existing methods ...

  // Email Verification
  verifyEmail = (token: string) =>
    this.axiosInstance.post('/auth/verify-email/', { token });

  // Password Reset
  requestPasswordReset = (email: string) =>
    this.axiosInstance.post('/auth/request-password-reset/', { email });

  confirmPasswordReset = (token: string, newPassword: string) =>
    this.axiosInstance.post('/auth/confirm-password-reset/', {
      token,
      new_password: newPassword
    });
}
```

---

## 🎨 UI Components Needed

### 1. Verify Email Page
**Route:** `/verify-email/:token`

Features:
- Auto-verify on page load
- Show loading spinner
- Display success/error message
- Redirect after verification

### 2. Verify Email Sent Page
**Route:** `/verify-email-sent`

Features:
- Confirmation message
- "Resend verification email" button
- Link to go to dashboard

### 3. Forgot Password Page
**Route:** `/forgot-password`

Features:
- Email input form
- Submit button
- Success message with instructions

### 4. Reset Password Page
**Route:** `/reset-password/:token`

Features:
- New password input
- Confirm password input
- Submit button
- Token from URL params

---

## 📝 Environment Variables

Update frontend `.env`:
```env
VITE_API_URL=http://localhost:8000/api
VITE_FRONTEND_URL=http://localhost:3000
```

---

## 🔒 Protected Routes (Optional)

Consider requiring email verification for certain actions:

```typescript
// Check if email is verified
const isVerified = user?.is_verified || false;

// Show verification reminder
if (!isVerified) {
  return (
    <div className="verification-banner">
      Please verify your email to access all features.
      <button onClick={resendVerification}>Resend Email</button>
    </div>
  );
}
```

---

## ✨ Enhanced UX Suggestions

### 1. Resend Verification Email
```typescript
const resendVerification = async () => {
  try {
    // You can add a backend endpoint for this
    await api.post('/auth/resend-verification/');
    toast.success('Verification email resent!');
  } catch (error) {
    toast.error('Failed to resend');
  }
};
```

### 2. Email Verification Status
Show verification badge in user profile:
```typescript
<div className="profile-header">
  {user.is_verified ? (
    <Badge color="green">✓ Verified</Badge>
  ) : (
    <Badge color="yellow">⚠ Not Verified</Badge>
  )}
</div>
```

### 3. Password Reset Flow
Complete flow with loading states:
```typescript
const [step, setStep] = useState<'form' | 'sent' | 'reset'>('form');

// Step 1: Request reset
if (step === 'form') {
  return <EmailForm onSubmit={handleRequestReset} />;
}

// Step 2: Confirmation
if (step === 'sent') {
  return <CheckYourEmail />;
}

// Step 3: Reset form
if (step === 'reset') {
  return <ResetForm onSubmit={handleReset} />;
}
```

---

## 🧪 Testing Checklist

- [ ] User can request password reset
- [ ] Reset email contains correct link
- [ ] Reset link opens correct page with token
- [ ] User can set new password
- [ ] Can login with new password
- [ ] Registration sends verification email
- [ ] Verification link works
- [ ] Verified user can access all features
- [ ] Error handling for invalid/expired tokens
- [ ] Loading states during API calls

---

## 📱 Email Links Format

Your email links should point to:

```
Verification: http://localhost:3000/verify-email/{token}
Password Reset: http://localhost:3000/reset-password/{token}
```

Make sure these routes exist in your React Router config:

```typescript
<Routes>
  {/* ... existing routes ... */}
  <Route path="/verify-email/:token" element={<VerifyEmailPage />} />
  <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
  <Route path="/verify-email-sent" element={<VerifyEmailSentPage />} />
  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
</Routes>
```

---

## 🎯 Quick Implementation Order

1. **Phase 1: Setup**
   - Add API methods to client
   - Create route structure

2. **Phase 2: Password Reset**
   - Build forgot password page
   - Build reset password page
   - Test complete flow

3. **Phase 3: Email Verification**
   - Build verify email page
   - Add post-registration message
   - Test verification flow

4. **Phase 4: Polish**
   - Add loading states
   - Improve error messages
   - Add resend functionality
   - Add verification badges

---

## 🆘 Troubleshooting

**Issue:** Token not working
- Check token is extracted correctly from URL
- Verify token hasn't expired (1 hour for reset tokens)
- Check API is receiving full token

**Issue:** CORS errors
- Ensure backend CORS settings include frontend URL
- Check credentials are being sent

**Issue:** Email not received
- Check SMTP2GO credentials in backend
- Verify FROM_EMAIL is configured
- Check spam folder

---

**Last Updated:** March 3, 2026  
**Backend Version:** Complete ✅  
**Status:** Ready for Frontend Integration
