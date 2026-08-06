import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const MODULE = "res_radlex_parsing.extraction.tools";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "query_radlex_graph",
    label: "Search RadLex",
    description: "Search RadLex concept labels/synonyms for a text match.",
    parameters: Type.Object({
      text: Type.String({ description: "Text to search for" }),
      limit: Type.Optional(Type.Number({ description: "Max results (default 10)" })),
    }),
    async execute(toolCallId, params, signal) {
      const args = ["run", "python", "-m", MODULE, "search", "--text", params.text];
      if (params.limit) args.push("--limit", String(params.limit));
      const result = await pi.exec("uv", args, { signal });
      return {
        content: [{ type: "text", text: result.stdout || result.stderr }],
        details: { exitCode: result.code },
      };
    },
  });

  pi.registerTool({
    name: "get_concept",
    label: "Get RadLex Concept",
    description:
      "Look up a RadLex concept's attributes and immediate parents/children by RID.",
    parameters: Type.Object({
      rid: Type.String({ description: "RadLex identifier, e.g. RID1327" }),
    }),
    async execute(toolCallId, params, signal) {
      const result = await pi.exec(
        "uv",
        ["run", "python", "-m", MODULE, "get-concept", "--rid", params.rid],
        { signal }
      );
      return {
        content: [{ type: "text", text: result.stdout || result.stderr }],
        details: { exitCode: result.code },
      };
    },
  });

  pi.registerTool({
    name: "propose_concept",
    label: "Propose RadLex Concept",
    description:
      "Record a candidate new RadLex concept not currently in the graph, for later review.",
    parameters: Type.Object({
      name: Type.String({ description: "Proposed concept name" }),
      parentRid: Type.String({
        description: "RID of the suggested parent concept (the candidate's is_a placement)",
      }),
      rationale: Type.String({ description: "Why this concept appears to be missing" }),
      relationships: Type.Optional(
        Type.Array(
          Type.Object({
            relationType: Type.String({
              description: "Relation type, e.g. Part_Of, Branch_Of, Contained_In, Member_Of",
            }),
            targetRid: Type.String({
              description: "RID of the existing concept this relation points to",
            }),
          }),
          { description: "Additional non-hierarchy relations for the candidate, beyond is_a" }
        )
      ),
    }),
    async execute(toolCallId, params, signal) {
      const relationships = (params.relationships ?? []).map((r) => ({
        relation_type: r.relationType,
        target_rid: r.targetRid,
      }));
      const result = await pi.exec(
        "uv",
        [
          "run", "python", "-m", MODULE, "propose-concept",
          "--name", params.name,
          "--parent-rid", params.parentRid,
          "--rationale", params.rationale,
          "--relationships", JSON.stringify(relationships),
        ],
        { signal }
      );
      return {
        content: [{ type: "text", text: result.stdout || result.stderr }],
        details: { exitCode: result.code },
      };
    },
  });
}
