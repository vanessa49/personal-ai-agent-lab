/**
 * 路径配置文件
 * 
 * 使用方式：
 * 1. 在 Docker 容器内：自动使用 /ai-agent/ 路径
 * 2. 在本地/NAS：通过环境变量或命令行参数指定
 * 
 * 环境变量：
 *   PROJECT_ROOT - 项目根目录（默认：当前目录）
 *   DATA_DIR - 数据目录（默认：PROJECT_ROOT/data）
 */

const path = require('path');
const fs = require('fs');

// 检测是否在 Docker 容器内
function isInDocker() {
  try {
    return fs.existsSync('/.dockerenv') || 
           fs.existsSync('/proc/1/cgroup') && 
           fs.readFileSync('/proc/1/cgroup', 'utf8').includes('docker');
  } catch {
    return false;
  }
}

// 获取项目根目录
function getProjectRoot() {
  // 1. 环境变量指定
  if (process.env.PROJECT_ROOT) {
    return process.env.PROJECT_ROOT;
  }
  
  // 2. Docker 容器内
  if (isInDocker()) {
    return '/ai-agent';
  }
  
  // 3. 本地开发：从脚本位置向上查找
  const scriptDir = __dirname;
  const projectRoot = path.resolve(scriptDir, '..');
  return projectRoot;
}

// 获取数据目录
function getDataDir() {
  if (process.env.DATA_DIR) {
    return process.env.DATA_DIR;
  }
  
  const root = getProjectRoot();
  
  // Docker 容器内使用固定路径
  if (isInDocker()) {
    return root;
  }
  
  // 本地使用 data 子目录
  return path.join(root, 'data');
}

const PROJECT_ROOT = getProjectRoot();
const DATA_DIR = getDataDir();

module.exports = {
  // 项目根目录
  PROJECT_ROOT,
  
  // 数据根目录
  DATA_DIR,
  
  // 对话数据
  CONVERSATIONS_DIR: path.join(DATA_DIR, 'memory', 'conversations'),
  
  // 训练数据
  TRAINING_DIR: path.join(DATA_DIR, 'training'),
  DATASET_DIR: path.join(DATA_DIR, 'training', 'dataset'),
  COGNITIVE_DIR: path.join(DATA_DIR, 'training', 'cognitive'),
  GRAPHS_DIR: path.join(DATA_DIR, 'training', 'cognitive', 'graphs'),
  
  // 训练数据集文件
  SAMPLES_FILE: path.join(DATA_DIR, 'training', 'dataset', 'samples.jsonl'),
  PENDING_FILE: path.join(DATA_DIR, 'training', 'dataset', 'pending_review.jsonl'),
  REJECTED_FILE: path.join(DATA_DIR, 'training', 'dataset', 'rejected.jsonl'),
  AGENT_REVIEWED_FILE: path.join(DATA_DIR, 'training', 'dataset', 'agent_reviewed.jsonl'),
  DISAGREEMENT_FILE: path.join(DATA_DIR, 'training', 'dataset', 'human_agent_disagreement.jsonl'),
  
  // 认知切分输出
  COGNITIVE_SAMPLES_FILE: path.join(DATA_DIR, 'training', 'cognitive', 'cognitive_samples.jsonl'),
  
  // 日志
  LOGS_DIR: path.join(DATA_DIR, 'logs'),
  BATCH_LOG: path.join(DATA_DIR, 'logs', 'batch_process.log'),
  AGENT_REVIEW_LOG: path.join(DATA_DIR, 'logs', 'agent_review.log'),
  
  // 技能
  SKILLS_DIR: path.join(DATA_DIR, 'skills'),
  
  // Seeds（原始导入数据）
  SEEDS_DIR: path.join(DATA_DIR, 'seeds'),
  
  // 工具函数：确保目录存在
  ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }
    return dirPath;
  },
  
  // 工具函数：初始化所有必要目录
  initDirs() {
    this.ensureDir(this.DATA_DIR);
    this.ensureDir(this.CONVERSATIONS_DIR);
    this.ensureDir(this.TRAINING_DIR);
    this.ensureDir(this.DATASET_DIR);
    this.ensureDir(this.COGNITIVE_DIR);
    this.ensureDir(this.GRAPHS_DIR);
    this.ensureDir(this.LOGS_DIR);
    this.ensureDir(this.SKILLS_DIR);
    this.ensureDir(this.SEEDS_DIR);
  },
  
  // 调试信息
  debug() {
    console.log('路径配置:');
    console.log(`  项目根目录: ${this.PROJECT_ROOT}`);
    console.log(`  数据目录: ${this.DATA_DIR}`);
    console.log(`  对话目录: ${this.CONVERSATIONS_DIR}`);
    console.log(`  训练目录: ${this.TRAINING_DIR}`);
    console.log(`  认知图谱: ${this.GRAPHS_DIR}`);
    console.log(`  Docker 环境: ${isInDocker() ? '是' : '否'}`);
  }
};
