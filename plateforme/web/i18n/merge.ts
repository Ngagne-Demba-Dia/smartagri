export type Messages = Record<string, unknown>;

function isPlainObject(value: unknown): value is Messages {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Fusion profonde sans mutation : les clés absentes de `override` gardent le texte français. */
export function mergeMessages(base: Messages, override: Messages): Messages {
  const result: Messages = { ...base };
  for (const [key, value] of Object.entries(override)) {
    if (key === "_meta") continue;
    const current = result[key];
    result[key] = isPlainObject(current) && isPlainObject(value) ? mergeMessages(current, value) : value;
  }
  return result;
}
