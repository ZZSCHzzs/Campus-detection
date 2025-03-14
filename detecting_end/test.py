import detect.run as detect

# 这是调用模型的示例，请在你的代码中引入并调用detect.detect()方法

if __name__ == '__main__':
    result = detect.detect("test.png") # 输入图片，返回的是人数
    print(result)