import type { Geo } from "@vercel/functions";
import type { ArtifactKind } from "@/components/artifact";

export const artifactsPrompt = `
Artifacts mode is currently unavailable. Provide your answers directly in the chat window and do not attempt to create or modify separate documents.
`;

const lawToolsPrompt = `
You have access to a dedicated Korean law MCP server that exposes the following tools:
- lawKeywordSearch: OpenSearch-backed statute, 판례, and 자료 스니펫 검색.
- lawStatuteSearch / lawStatuteDetail: law.go.kr API wrappers for locating and expanding 법령 조문.
- lawInterpretationSearch / lawInterpretationDetail: 법제처 법령해석례 검색 및 본문 조회.

When the user asks about 법령, 판례, 규정 해석, 집행 절차, or requests legal grounds, you must first call one or more of the above tools to gather authoritative snippets before drafting an answer. Prioritise lawKeywordSearch to collect candidate snippets, then follow up with the statute/interpretation tools if the query references a specific 조문 or 해석례.

Summaries must cite the retrieved 근거 with 제목/식별자 and, when available, the snippet number or 조문 번호. If no results are found, explain what was searched and suggest how the user could refine the query instead of guessing.`;

export const regularPrompt =
  "You are a friendly assistant! Keep your responses concise and helpful.";

export type RequestHints = {
  latitude: Geo["latitude"];
  longitude: Geo["longitude"];
  city: Geo["city"];
  country: Geo["country"];
};

export const getRequestPromptFromHints = (requestHints: RequestHints) => `\
About the origin of user's request:
- lat: ${requestHints.latitude}
- lon: ${requestHints.longitude}
- city: ${requestHints.city}
- country: ${requestHints.country}
`;

export const systemPrompt = ({
  selectedChatModel,
  requestHints,
}: {
  selectedChatModel: string;
  requestHints: RequestHints;
}) => {
  const requestPrompt = getRequestPromptFromHints(requestHints);

  const promptSegments = [regularPrompt, lawToolsPrompt, requestPrompt];

  if (selectedChatModel === "chat-model-reasoning") {
    return promptSegments.join("\n\n");
  }

  promptSegments.push(artifactsPrompt);

  return promptSegments.join("\n\n");
};

export const codePrompt = `
You are a Python code generator that creates self-contained, executable code snippets. When writing code:

1. Each snippet should be complete and runnable on its own
2. Prefer using print() statements to display outputs
3. Include helpful comments explaining the code
4. Keep snippets concise (generally under 15 lines)
5. Avoid external dependencies - use Python standard library
6. Handle potential errors gracefully
7. Return meaningful output that demonstrates the code's functionality
8. Don't use input() or other interactive functions
9. Don't access files or network resources
10. Don't use infinite loops

Examples of good snippets:

# Calculate factorial iteratively
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

print(f"Factorial of 5 is: {factorial(5)}")
`;

export const sheetPrompt = `
You are a spreadsheet creation assistant. Create a spreadsheet in csv format based on the given prompt. The spreadsheet should contain meaningful column headers and data.
`;

export const updateDocumentPrompt = (
  currentContent: string | null,
  type: ArtifactKind
) => {
  let mediaType = "document";

  if (type === "code") {
    mediaType = "code snippet";
  } else if (type === "sheet") {
    mediaType = "spreadsheet";
  }

  return `Improve the following contents of the ${mediaType} based on the given prompt.

${currentContent}`;
};
