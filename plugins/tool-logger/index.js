const fs = require("node:fs/promises");
const path = require("node:path");
const LOG_FILE = "/ai-agent/logs/tool_calls.log";

function ts() {
  return new Date().toISOString().replace("T"," ").substring(0,19);
}

function register(api) {
  api.on("before_tool_call", async function(event) {
    try {
      await fs.mkdir(path.dirname(LOG_FILE), {recursive:true});
      let line = "[" + ts() + "] 开始 | 工具: " + event.toolName;
      const p = event.params || {};
      if (p.path) line += " | 路径: " + p.path;
      if (p.command) line += " | 命令: " + String(p.command).substring(0,80);
      await fs.appendFile(LOG_FILE, line + "\n", "utf-8");
    } catch(e) { console.error("[tool-logger] error:", e); }
  });

  api.on("after_tool_call", async function(event) {
    try {
      await fs.mkdir(path.dirname(LOG_FILE), {recursive:true});
      let line = "[" + ts() + "] " + (event.error?"失败":"完成") + " | 工具: " + event.toolName;
      const p = event.params || {};
      if (p.path) line += " | 路径: " + p.path;
      if (event.error) line += " | 错误: " + event.error;
      await fs.appendFile(LOG_FILE, line + "\n", "utf-8");
    } catch(e) { console.error("[tool-logger] error:", e); }
  });

  console.log("[tool-logger] Plugin 已加载");
}

module.exports = register;
