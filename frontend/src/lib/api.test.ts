import { describe, expect, it } from "vitest";
import { ApiError, api, normalizeList } from "./api";

describe("normalizeList", () => {
  it("preserves API list data and metadata", () => {
    const meta = { request_id: "request-1", next_cursor: "cursor-2" };
    expect(normalizeList([{ id: "event-1" }], meta)).toEqual({
      data: [{ id: "event-1" }],
      meta,
    });
  });

  it("accepts paginated API payloads", () => {
    expect(normalizeList({ items: [{ id: "incident-1" }] }, { request_id: "request-2" }).data)
      .toEqual([{ id: "incident-1" }]);
  });

  it("rejects malformed list payloads instead of manufacturing an empty list", () => {
    expect(() => normalizeList({}, {})).toThrow(ApiError);
  });

  it("requires the server-issued idempotency key before simulated execution", () => {
    expect(() => api.responseAction("response-1", "execute")).toThrow(ApiError);
  });
});
