export const ONBOARDED_COOKIE = "cartwise_onboarded";
export const ONBOARDED_VALUE = "1";

export const ONBOARDED_COOKIE_OPTIONS = {
  path: "/",
  httpOnly: false,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  maxAge: 60 * 60 * 24 * 365,
};
