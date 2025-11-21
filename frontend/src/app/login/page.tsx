import Link from "next/link";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white p-8 rounded-xl shadow">
        <h1 className="text-2xl font-semibold mb-6 text-center">
          CompanyBuddy Login
        </h1>

        <form className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            className="w-full p-3 rounded border"
          />

          <input
            type="password"
            placeholder="Password"
            className="w-full p-3 rounded border"
          />

          <button
            type="submit"
            className="w-full bg-blue-600 text-white p-3 rounded font-semibold"
          >
            Sign in
          </button>
        </form>

        <div className="my-6 text-center text-gray-500">or</div>

        <a
          href="http://localhost:8000/api/v1/auth/login/google"
          className="w-full flex justify-center items-center p-3 border rounded hover:bg-gray-100"
        >
          <img
            src="https://www.svgrepo.com/show/475656/google-color.svg"
            className="w-5 h-5 mr-2"
          />
          Sign in with Google
        </a>
      </div>
    </div>
  );
}
