import { describe, expect, it } from "vitest";
import { domainQuotaLabel, quotaLabel, quotaState } from "@/lib/quota";

describe("quotaState", () => {
  it("is ok below 80%", () => {
    expect(quotaState(0, 5)).toBe("ok");
    expect(quotaState(3, 5)).toBe("ok");
  });

  it("warns at 80% and above", () => {
    expect(quotaState(4, 5)).toBe("warning");
    expect(quotaState(8, 10)).toBe("warning");
  });

  it("stays ok below 80%", () => {
    expect(quotaState(1, 2)).toBe("ok");
  });

  it("is exhausted at the limit", () => {
    expect(quotaState(5, 5)).toBe("exhausted");
    expect(quotaState(0, 0)).toBe("exhausted");
  });
});

describe("labels", () => {
  it("uses explicit text, not color alone", () => {
    expect(quotaLabel(2, 5)).toBe("2 of 5 scans used this period");
    expect(domainQuotaLabel(1, 2)).toBe("1 of 2 domains");
    expect(domainQuotaLabel(2, 2)).toBe("2 of 2 domains — limit reached");
  });
});
