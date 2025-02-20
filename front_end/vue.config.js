const { defineConfig } = require('@vue/cli-service');

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    allowedHosts: [
      'smarthit.top', // 允许的域名
      'localhost',      // 允许本地访问
      '127.0.0.1',      // 允许本地访问
      '47.93.243.92',  // 允许通过 IP 访问（替换为你的服务器 IP）
    ],
    // 如果需要禁用主机检查（不推荐），可以取消注释以下行
    // disableHostCheck: true,
  },
});