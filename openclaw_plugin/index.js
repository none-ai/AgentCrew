import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { definePluginEntry } from "openclaw";

const DEFAULT_CONFIG = {
  baseUrl: "http://127.0.0.1:8765",
  autoStart: false,
  pythonExecutable: "python",
  projectRoot: process.cwd(),
  host: "127.0.0.1",
  port: 8765,
};

function mergeConfig(api, context) {
  const runtimeConfig =
    context?.config ??
    api?.getConfig?.() ??
    api?.config ??
    {};

  const merged = { ...DEFAULT_CONFIG, ...runtimeConfig };
  if (!merged.baseUrl) {
    merged.baseUrl = `http://${merged.host}:${merged.port}`;
  }
  return merged;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `${response.status} ${response.statusText}`);
  }
  return payload;
}

async function waitForHealth(config) {
  for (let index = 0; index < 20; index += 1) {
    try {
      return await fetchJson(`${config.baseUrl}/health`);
    } catch (error) {
      await delay(500);
    }
  }

  throw new Error("AgentCrew service did not become healthy in time");
}

async function ensureService(config, api) {
  try {
    return await fetchJson(`${config.baseUrl}/health`);
  } catch (error) {
    if (!config.autoStart) {
      throw error;
    }
  }

  api?.logger?.info?.("Starting AgentCrew standalone service");
  const child = spawn(
    config.pythonExecutable,
    [
      "-m",
      "AgentCrew",
      "serve",
      "--host",
      config.host,
      "--port",
      String(config.port),
    ],
    {
      cwd: config.projectRoot,
      detached: true,
      stdio: "ignore",
    },
  );
  child.unref();

  return waitForHealth(config);
}

function toolResult(payload) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(payload, null, 2),
      },
    ],
    structuredContent: payload,
    data: payload,
  };
}

async function createTask(api, context, input) {
  const config = mergeConfig(api, context);
  await ensureService(config, api);
  const payload = await fetchJson(`${config.baseUrl}/tasks`, {
    method: "POST",
    body: JSON.stringify(input),
  });
  return toolResult(payload);
}

async function executeTask(api, context, input) {
  const config = mergeConfig(api, context);
  await ensureService(config, api);
  const payload = await fetchJson(`${config.baseUrl}/tasks/${input.taskId}/execute`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  return toolResult(payload);
}

async function serviceHealth(api, context) {
  const config = mergeConfig(api, context);
  const payload = await ensureService(config, api);
  return toolResult(payload);
}

export default definePluginEntry({
  id: "agentcrew",
  name: "AgentCrew",
  register(api) {
    const createHandler = async (input, context) => createTask(api, context, input);
    const executeHandler = async (input, context) => executeTask(api, context, input);
    const healthHandler = async (_input, context) => serviceHealth(api, context);

    api.registerTool({
      id: "agentcrew.create_task",
      name: "agentcrew.create_task",
      description: "Create a task in the AgentCrew standalone service.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        required: ["title"],
        properties: {
          title: { type: "string" },
          description: { type: "string" },
          task_type: { type: "string" },
          assignee: { type: "string" },
          command: {
            oneOf: [
              { type: "string" },
              { type: "array", items: { type: "string" } }
            ]
          },
          cwd: { type: "string" },
          timeout: { type: "integer" },
          metadata: { type: "object" }
        }
      },
      execute: createHandler,
      run: createHandler,
      handler: createHandler,
    });

    api.registerTool({
      id: "agentcrew.execute_task",
      name: "agentcrew.execute_task",
      description: "Execute an existing AgentCrew task by id.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        required: ["taskId"],
        properties: {
          taskId: { type: "string" }
        }
      },
      execute: executeHandler,
      run: executeHandler,
      handler: executeHandler,
    });

    api.registerTool({
      id: "agentcrew.health",
      name: "agentcrew.health",
      description: "Check whether the AgentCrew standalone service is running.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        properties: {}
      },
      execute: healthHandler,
      run: healthHandler,
      handler: healthHandler,
    });
  },
});
