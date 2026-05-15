import { describe, it, expect } from "vitest";
import { isValidReturnTo } from "../cookies";

describe("isValidReturnTo", () => {
  it("accepts valid relative paths", () => {
    expect(isValidReturnTo("/import?supplier=cartwise/starter")).toBe(true);
    expect(isValidReturnTo("/meal-plan")).toBe(true);
    expect(isValidReturnTo("/orders/123/expense")).toBe(true);
  });

  it("rejects undefined/empty", () => {
    expect(isValidReturnTo(undefined)).toBe(false);
    expect(isValidReturnTo("")).toBe(false);
  });

  it("rejects absolute URLs (open redirect)", () => {
    expect(isValidReturnTo("https://evil.com")).toBe(false);
    expect(isValidReturnTo("http://evil.com/path")).toBe(false);
  });

  it("rejects protocol-relative URLs", () => {
    expect(isValidReturnTo("//evil.com/path")).toBe(false);
  });

  it("rejects auth routes (prevent loops)", () => {
    expect(isValidReturnTo("/login")).toBe(false);
    expect(isValidReturnTo("/login?error=backend")).toBe(false);
    expect(isValidReturnTo("/auth/callback")).toBe(false);
    expect(isValidReturnTo("/onboarding")).toBe(false);
    expect(isValidReturnTo("/onboarding?splitwise=error")).toBe(false);
  });

  it("rejects paths not starting with /", () => {
    expect(isValidReturnTo("import")).toBe(false);
    expect(isValidReturnTo("meal-plan")).toBe(false);
  });

  it("rejects overly long paths", () => {
    expect(isValidReturnTo("/" + "a".repeat(2048))).toBe(false);
  });
});
