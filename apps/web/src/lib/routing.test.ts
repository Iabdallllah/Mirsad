import { describe, expect, it } from "vitest";
import { decideRoute, isPublicPath, safeNextPath } from "@/lib/routing";

describe("isPublicPath", () => {
  it("allows sign-in and auth callbacks only", () => {
    expect(isPublicPath("/sign-in")).toBe(true);
    expect(isPublicPath("/auth/callback")).toBe(true);
    expect(isPublicPath("/dashboard")).toBe(false);
    expect(isPublicPath("/authz")).toBe(false);
  });
});

describe("decideRoute", () => {
  it("sends unauthenticated users to sign-in with the deep link preserved", () => {
    expect(decideRoute({ pathname: "/issues/abc", authenticated: false })).toEqual({
      action: "redirect",
      pathname: "/sign-in",
      next: "/issues/abc",
    });
  });

  it("allows unauthenticated access to sign-in", () => {
    expect(decideRoute({ pathname: "/sign-in", authenticated: false })).toEqual({
      action: "allow",
    });
  });

  it("sends authenticated users away from sign-in", () => {
    expect(decideRoute({ pathname: "/sign-in", authenticated: true })).toEqual({
      action: "redirect",
      pathname: "/dashboard",
    });
  });

  it("allows authenticated app routes", () => {
    expect(decideRoute({ pathname: "/domains/new", authenticated: true })).toEqual({
      action: "allow",
    });
  });
});

describe("safeNextPath", () => {
  it("defaults to the dashboard", () => {
    expect(safeNextPath(null)).toBe("/dashboard");
    expect(safeNextPath("")).toBe("/dashboard");
  });

  it("keeps same-origin absolute paths", () => {
    expect(safeNextPath("/issues?severity=critical")).toBe("/issues?severity=critical");
  });

  it("blocks open-redirect targets", () => {
    expect(safeNextPath("//evil.example")).toBe("/dashboard");
    expect(safeNextPath("https://evil.example")).toBe("/dashboard");
    expect(safeNextPath("/\\evil.example")).toBe("/dashboard");
    expect(safeNextPath("javascript:alert(1)")).toBe("/dashboard");
  });

  it("blocks auth loops", () => {
    expect(safeNextPath("/sign-in")).toBe("/dashboard");
    expect(safeNextPath("/auth/callback")).toBe("/dashboard");
  });
});
