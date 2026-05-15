export const ONBOARDED_COOKIE = "cartwise_onboarded";
export const ONBOARDED_VALUE = "1";

export const ONBOARDED_COOKIE_OPTIONS = {
  path: "/",
  httpOnly: false,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  maxAge: 60 * 60 * 24 * 365,
};

export const RETURN_TO_COOKIE = "cartwise_return_to";

export const RETURN_TO_COOKIE_OPTIONS = {
  path: "/",
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  maxAge: 60 * 10,
};

export function isValidReturnTo(value: string | undefined): value is string {
  if (!value) return false;
  if (!value.startsWith("/")) return false;
  if (value.startsWith("//")) return false;
  if (value.includes("://")) return false;
  if (value.length > 2048) return false;
  if (value.startsWith("/login")) return false;
  if (value.startsWith("/auth")) return false;
  if (value.startsWith("/onboarding")) return false;
  return true;
}
