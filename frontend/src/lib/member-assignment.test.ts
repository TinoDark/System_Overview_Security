import { describe, expect, it } from "vitest";
import {
  initialPick,
  rolesFor,
  selectEveryOrganization,
  toggleOrganization,
} from "./member-assignment";

describe("member assignment", () => {
  it("preselects the only administered organization", () => {
    expect(initialPick(["org-a"])).toEqual({ "org-a": "soc_analyst" });
  });

  it("starts empty when several organizations can be chosen", () => {
    expect(initialPick(["org-a", "org-b"])).toEqual({});
  });

  it("keeps a chosen role when selecting the remaining organizations", () => {
    const picked = selectEveryOrganization({ "org-a": "auditor" }, ["org-a", "org-b"]);
    expect(picked).toEqual({ "org-a": "auditor", "org-b": "soc_analyst" });
  });

  it("removes an organization without touching the others", () => {
    expect(toggleOrganization({ "org-a": "operator", "org-b": "auditor" }, "org-a")).toEqual({
      "org-b": "auditor",
    });
  });

  it("lets a caller assign only their rank and the ranks below", () => {
    expect(rolesFor({ role: "security_admin" })).toEqual([
      "security_admin",
      "soc_analyst",
      "operator",
      "auditor",
      "observer",
    ]);
    expect(rolesFor({ role: "super_admin" })[0]).toBe("super_admin");
    expect(rolesFor({ role: "observer" })).toEqual(["observer"]);
  });
});
