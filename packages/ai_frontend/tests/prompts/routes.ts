import { generateUUID } from "@/lib/utils";

export const TEST_PROMPTS = {
  SKY: {
    MESSAGE: {
      id: generateUUID(),
      createdAt: new Date().toISOString(),
      role: "user",
      content: "Why is the sky blue?",
      parts: [{ type: "text", text: "Why is the sky blue?" }],
    },
    OUTPUT_STREAM: [
      'data: {"type":"start-step"}',
      'data: {"type":"text-start","id":"STATIC_ID"}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"It\'s "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"just "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"blue "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"duh! "}',
      'data: {"type":"text-end","id":"STATIC_ID"}',
      'data: {"type":"finish-step"}',
      'data: {"type":"finish"}',
      "data: [DONE]",
    ],
  },
  GRASS: {
    MESSAGE: {
      id: generateUUID(),
      createdAt: new Date().toISOString(),
      role: "user",
      content: "Why is grass green?",
      parts: [{ type: "text", text: "Why is grass green?" }],
    },
    OUTPUT_STREAM: [
      'data: {"type":"start-step"}',
      'data: {"type":"text-start","id":"STATIC_ID"}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"It\'s "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"just "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"green "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"duh! "}',
      'data: {"type":"text-end","id":"STATIC_ID"}',
      'data: {"type":"finish-step"}',
      'data: {"type":"finish"}',
      "data: [DONE]",
    ],
  },
  MULTI_TOOL_SUCCESS: {
    MESSAGE: {
      id: generateUUID(),
      createdAt: new Date().toISOString(),
      role: "user",
      content:
        "Summarize the tenant protection statutes with relevant commentary.",
      parts: [
        {
          type: "text",
          text: "Summarize the tenant protection statutes with relevant commentary.",
        },
      ],
    },
    OUTPUT_STREAM: [
      'data: {"type":"start-step"}',
      'data: {"type":"tool-input-available","toolCallId":"call_statute_search","toolName":"lawStatuteSearch","input":"{\\"query\\":\\"tenant protections\\"}"}',
      'data: {"type":"tool-output-available","toolCallId":"call_statute_search","output":{"type":"json","value":{"hits":[{"id":"statute-101","title":"Tenant Protection Act"},{"id":"statute-202","title":"Rental Fairness Ordinance"}]}}}',
      'data: {"type":"tool-input-available","toolCallId":"call_interpretation_detail","toolName":"lawInterpretationDetail","input":"{\\"interpretationId\\":\\"interp-314\\"}"}',
      'data: {"type":"tool-output-available","toolCallId":"call_interpretation_detail","output":{"type":"json","value":{"id":"interp-314","holding":"Courts interpret the act to require proactive notice to tenants about rent increases."}}}',
      'data: {"type":"finish-step"}',
      'data: {"type":"start-step"}',
      'data: {"type":"text-start","id":"STATIC_ID"}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"Tenant "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"protections "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"stem "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"from "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"the "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"Tenant "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"Protection "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"Act "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"and "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"subsequent "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"interpretations "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"requiring "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"proactive "}',
      'data: {"type":"text-delta","id":"STATIC_ID","delta":"notice. "}',
      'data: {"type":"text-end","id":"STATIC_ID"}',
      'data: {"type":"finish-step"}',
      'data: {"type":"finish"}',
      "data: [DONE]",
    ],
  },
  MULTI_TOOL_FAILURE: {
    MESSAGE: {
      id: generateUUID(),
      createdAt: new Date().toISOString(),
      role: "user",
      content: "Summarize the statutes but keep calling tools forever.",
      parts: [
        {
          type: "text",
          text: "Summarize the statutes but keep calling tools forever.",
        },
      ],
    },
  },
};
