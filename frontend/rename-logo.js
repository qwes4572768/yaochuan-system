// 一次性腳本：將 brand-logo.png.png 重新命名為 brand-logo.png（標準單一 .png）
const fs = require('fs')
const path = require('path')
const oldPath = path.join(__dirname, 'src', 'assets', 'brand-logo.png.png')
const newPath = path.join(__dirname, 'src', 'assets', 'brand-logo.png')
if (fs.existsSync(oldPath)) {
  fs.renameSync(oldPath, newPath)
  console.log('已重新命名：brand-logo.png.png -> brand-logo.png')
} else if (fs.existsSync(newPath)) {
  console.log('brand-logo.png 已存在，無需重新命名')
} else {
  console.error('找不到 src/assets/brand-logo.png.png')
  process.exit(1)
}
