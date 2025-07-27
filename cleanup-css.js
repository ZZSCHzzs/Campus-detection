const fs = require('fs');
const path = require('path');

// 要处理的Vue文件路径
const vueFilePath = path.join(__dirname, 'front_end', 'src', 'views', 'DataScreen.vue');
// 清理后输出的文件路径
const outputFilePath = path.join(__dirname, 'front_end', 'src', 'views', 'DataScreen.cleaned.vue');

fs.readFile(vueFilePath, 'utf8', (err, content) => {
    if (err) {
        console.error(`Error reading file: ${vueFilePath}`, err);
        return;
    }

    // 1. 提取模板和样式部分
    const templateMatch = content.match(/<template>([\s\S]*?)<\/template>/);
    const styleMatch = content.match(/<style scoped>([\s\S]*?)<\/style>/);

    if (!templateMatch || !styleMatch) {
        console.error('Could not find <template> or <style scoped> blocks.');
        return;
    }

    const templateContent = templateMatch[1];
    const styleContent = styleMatch[1];

    // 2. 从模板中提取所有使用的类名
    const classRegex = /class="(.*?)"/g;
    let usedClasses = new Set();
    let match;
    while ((match = classRegex.exec(templateContent)) !== null) {
        match[1].split(/\s+/).forEach(cls => usedClasses.add(cls.trim()));
    }
    console.log('Used classes found in template:', Array.from(usedClasses));

    // 3. 清理未使用的CSS规则
    // 这个正则表达式尝试匹配CSS规则块，从选择器到 '}'
    const cssRuleRegex = /([^{}]+){([^{}]*)}/g;
    const cleanedStyleContent = styleContent.replace(cssRuleRegex, (rule, selector, body) => {
        // 提取选择器中的类名 (例如 .my-class, .class1.class2)
        const selectorClasses = selector.match(/\.([a-zA-Z0-9_-]+)/g) || [];
        
        if (selectorClasses.length === 0) {
            // 保留没有类选择器的规则 (例如 'div', '[data-v-xxx]')
            return rule;
        }

        // 检查这个规则中的所有类是否都在模板中使用过
        const isUsed = selectorClasses.every(cls => usedClasses.has(cls.substring(1)));

        if (isUsed) {
            return rule; // 保留使用的规则
        } else {
            console.log(`Removing unused rule: ${selector.trim()}`);
            return ''; // 移除未使用的规则
        }
    }).replace(/\n\s*\n/g, '\n'); // 清理多余的空行

    // 4. 构建新的文件内容
    const newContent = content.replace(styleMatch[0], `<style scoped>${cleanedStyleContent}</style>`);

    // 5. 写入新文件
    fs.writeFile(outputFilePath, newContent, 'utf8', (writeErr) => {
        if (writeErr) {
            console.error(`Error writing cleaned file: ${outputFilePath}`, writeErr);
            return;
        }
        console.log(`Successfully cleaned CSS and saved to: ${outputFilePath}`);
    });
});