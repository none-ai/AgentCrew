# AgentCrew OpenClaw Plugin

This native OpenClaw plugin bridges OpenClaw tool calls to the AgentCrew standalone HTTP service.

## Install

```bash
openclaw plugins install ./openclaw_plugin
openclaw gateway restart
```

## Configure

Example config:

```yaml
plugins:
  entries:
    agentcrew:
      enabled: true
      config:
        baseUrl: http://127.0.0.1:8765
        autoStart: true
        pythonExecutable: python
        projectRoot: /path/to/AgentCrew
        host: 127.0.0.1
        port: 8765
```

## Exposed tools

- `agentcrew.health`
- `agentcrew.create_task`
- `agentcrew.execute_task`

If `autoStart` is enabled, the plugin starts `python -m AgentCrew serve` before calling the service.
