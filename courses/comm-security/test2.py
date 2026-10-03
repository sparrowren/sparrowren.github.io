import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.models import Model

from PIL import Image
import matplotlib.pyplot as plt
import os


class ChaosImageEncryptor:
    def __init__(self):
        # 初始化DNA编码规则
        self.DNA_ENCODE_RULES = [
            {'00': 'A', '01': 'C', '10': 'G', '11': 'T'},  # 规则1
            {'00': 'A', '01': 'G', '10': 'C', '11': 'T'},  # 规则2
            {'00': 'C', '01': 'A', '10': 'T', '11': 'G'},  # 规则3
            {'00': 'C', '01': 'T', '10': 'A', '11': 'G'},  # 规则4
            {'00': 'G', '01': 'A', '10': 'T', '11': 'C'},  # 规则5
            {'00': 'G', '01': 'T', '10': 'A', '11': 'C'},  # 规则6
            {'00': 'T', '01': 'C', '10': 'G', '11': 'A'},  # 规则7
            {'00': 'T', '01': 'G', '10': 'C', '11': 'A'}  # 规则8
        ]

        self.DNA_DECODE_RULES = [
            {'A': '00', 'C': '01', 'G': '10', 'T': '11'},  # 规则1
            {'A': '00', 'G': '01', 'C': '10', 'T': '11'},  # 规则2
            {'C': '00', 'A': '01', 'T': '10', 'G': '11'},  # 规则3
            {'C': '00', 'T': '01', 'A': '10', 'G': '11'},  # 规则4
            {'G': '00', 'A': '01', 'T': '10', 'C': '11'},  # 规则5
            {'G': '00', 'T': '01', 'A': '10', 'C': '11'},  # 规则6
            {'T': '00', 'C': '01', 'G': '10', 'A': '11'},  # 规则7
            {'T': '00', 'G': '01', 'C': '10', 'A': '11'}  # 规则8
        ]
        self.DNA_XOR_RULES = {
            'A': {'A': 'A', 'G': 'G', 'C': 'C', 'T': 'T'},
            'G': {'A': 'G', 'G': 'A', 'C': 'T', 'T': 'C'},
            'C': {'A': 'C', 'G': 'T', 'C': 'A', 'T': 'G'},
            'T': {'A': 'T', 'G': 'C', 'C': 'G', 'T': 'A'}
        }
        # 初始化VGG16模型
        self.feature_model = self._build_feature_extractor()

        # 保存初始值用于解密
        self.initial_values = None
        self.main_key = None
        self.r1 = np.random.randint(0, 256)  # 扩散操作中的随机值

    def _build_feature_extractor(self):
        """构建VGG16特征提取器"""
        base_model = VGG16(weights='imagenet', include_top=True)
        model = Model(inputs=base_model.input,
                      outputs=base_model.get_layer('fc2').output)
        return model

    def _extract_features(self, image_path):
        """提取图像特征"""
        img = Image.open(image_path).resize((224, 224))

        # 如果图像有 alpha 通道（RGBA），转换为 RGB
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        img_array = np.expand_dims(preprocess_input(np.array(img)), axis=0)
        features = self.feature_model.predict(img_array)
        return features.flatten()

    def generate_main_key(self, image_path):
        """生成主密钥和混沌系统初始值（改为稳定的 0.1–0.9 区间）"""
        # 提取特征
        features = self._extract_features(image_path)
        # 仅使用前512维
        features = features[:512]

        # 二值化 + 随机异或
        binary_key = (features > 0.5).astype(np.uint8)
        random_key = np.random.randint(0, 2, size=binary_key.shape)
        self.main_key = np.bitwise_xor(binary_key, random_key)

        # reshape
        main_key_3d = self.main_key.reshape((8, 8, 8))

        # 计算原始初始值（0–1）
        F = np.mod(np.sum(main_key_3d, axis=2), 2)
        S = np.dot([128, 64, 32, 16, 8, 4, 2, 1], F)  # 0–255
        self.initial_values = 0.2 + 0.6 * (S[:4] / 255.0)  # 限制在0.2-0.8之间

        return self.initial_values, self.main_key

    def _lorenz_system(self, x0, y0, z0, w0, steps, dt=0.001):
        """超混沌Lorenz系统（采用4阶RK法进行数值积分，防止数值发散）"""
        # 参数设定（可根据需要调整）
        a = 10.0
        b = 8.0 / 3
        c = 28.0
        r = -1.0

        # 初始化变量（使用float64精度）
        x = np.empty(steps, dtype=np.float64)
        y = np.empty(steps, dtype=np.float64)
        z = np.empty(steps, dtype=np.float64)
        w = np.empty(steps, dtype=np.float64)
        x[0], y[0], z[0], w[0] = x0, y0, z0, w0

        # RK4积分
        for i in range(steps - 1):
            # 定义求导函数
            def derivatives(x_i, y_i, z_i, w_i):
                dx = a * (y_i - x_i) + w_i
                dy = c * x_i - y_i - x_i * z_i
                dz = x_i * y_i - b * z_i
                dw = -y_i * z_i + r * w_i
                return dx, dy, dz, dw

            # k1
            k1_x, k1_y, k1_z, k1_w = derivatives(x[i], y[i], z[i], w[i])
            # k2
            k2_x, k2_y, k2_z, k2_w = derivatives(
                x[i] + k1_x * dt / 2,
                y[i] + k1_y * dt / 2,
                z[i] + k1_z * dt / 2,
                w[i] + k1_w * dt / 2
            )
            # k3
            k3_x, k3_y, k3_z, k3_w = derivatives(
                x[i] + k2_x * dt / 2,
                y[i] + k2_y * dt / 2,
                z[i] + k2_z * dt / 2,
                w[i] + k2_w * dt / 2
            )
            # k4
            k4_x, k4_y, k4_z, k4_w = derivatives(
                x[i] + k3_x * dt,
                y[i] + k3_y * dt,
                z[i] + k3_z * dt,
                w[i] + k3_w * dt
            )

            # 更新状态值
            x[i + 1] = x[i] + (dt / 6) * (k1_x + 2 * k2_x + 2 * k3_x + k4_x)
            y[i + 1] = y[i] + (dt / 6) * (k1_y + 2 * k2_y + 2 * k3_y + k4_y)
            z[i + 1] = z[i] + (dt / 6) * (k1_z + 2 * k2_z + 2 * k3_z + k4_z)
            w[i + 1] = w[i] + (dt / 6) * (k1_w + 2 * k2_w + 2 * k3_w + k4_w)

            # 防止数值溢出以及检测异常
            if np.any(np.isnan([x[i + 1], y[i + 1], z[i + 1], w[i + 1]])) or \
                    np.abs(x[i + 1]) > 1e10 or np.abs(y[i + 1]) > 1e10 or np.abs(z[i + 1]) > 1e10 or np.abs(
                w[i + 1]) > 1e10:
                raise ValueError(f"混沌系统在步骤 {i + 1} 发散或数值异常")

        return x, y, z, w

    def _generate_chaos_sequences(self, M, N):
        """生成混沌序列"""
        if self.initial_values is None:
            raise ValueError("Initial values not generated. Call generate_main_key() first.")

        x0, y0, z0, w0 = self.initial_values
        steps = M * N + 10000  # 额外10000次迭代去除瞬态

        x, y, z, w = self._lorenz_system(x0, y0, z0, w0, steps)

        # 去除前1000个瞬态值
        x = x[1000:]
        y = y[1000:]
        z = z[1000:]
        w = w[1000:]

        # 生成伪随机矩阵
        X = np.zeros((M, N))
        Y = np.zeros((M, N))
        Z = np.zeros((M, N))
        W = np.zeros((M, N))
        U = np.zeros((M, N))
        V = np.zeros((M, N))
        T = np.zeros((M, N), dtype=np.uint8)

        for k in range(M):
            for l in range(N):
                idx = k * N + l
                X[k, l] = np.mod(np.floor(np.mod(x[idx] + 500, 1) * (10 ** 13)), 256)
                Y[k, l] = np.mod(np.floor(np.mod(y[idx] + 500, 1) * (10 ** 13)), 256)
                Z[k, l] = np.mod(np.floor(z[idx] * (10 ** 13)), M)
                W[k, l] = np.mod(np.floor(np.mod(w[idx] + 500, 1) * (10 ** 12)), N)
                U[k, l] = np.mod(np.floor(np.mod(x[idx] + y[idx] + 500, 1) * (10 ** 12)), M)
                V[k, l] = np.mod(np.floor(np.mod(z[idx] + w[idx] + 500, 1) * (10 ** 12)), N)
                T[k, l] = np.mod(np.floor(np.mod(x[idx] + w[idx] + 500, 1) * (10 ** 12)), 8) + 1

        return X, Y, Z, W, U, V, T

    def _dna_operations(self, pixel_value, chaos_value, rule_idx, operation='encode'):
        """统一的DNA操作函数：支持 encode 和 decode"""

        if operation == 'encode':
            binary = format(pixel_value, '08b')  # 8-bit
            rule = self.DNA_ENCODE_RULES[rule_idx - 1]
            dna = ""
            for i in range(0, 8, 2):
                bits = binary[i:i + 2]
                dna += rule[bits]
            return dna

        else:  # decode
            rule = self.DNA_ENCODE_RULES[rule_idx - 1]
            # 注意：我们现在假设 dna 是长度为 4 的碱基串，例如 'AGTC'
            inverse_rule = {v: k for k, v in rule.items()}
            binary = ""
            for base in pixel_value:
                if base not in inverse_rule:
                    raise ValueError(f"无法解码碱基 {base}，当前 rule={rule}")
                binary += inverse_rule[base]
            return int(binary, 2)

    def _dna_xor(self, dna1, dna2, rule_idx=None):
        """
        基于表2.5的DNA异或运算：直接使用碱基进行异或，无需转换为二进制。
        """
        xor_table = {
            'A': {'A': 'A', 'G': 'G', 'C': 'C', 'T': 'T'},
            'G': {'A': 'G', 'G': 'A', 'C': 'T', 'T': 'C'},
            'C': {'A': 'C', 'G': 'T', 'C': 'A', 'T': 'G'},
            'T': {'A': 'T', 'G': 'C', 'C': 'G', 'T': 'A'}
        }

        result_dna = ""
        for base1, base2 in zip(dna1, dna2):
            result_dna += xor_table[base1][base2]
        return result_dna

        # === 新增置乱功能 ===

        # === 新增置乱功能 ===

    def _scrambling_operation(self, A, U, V, Z, W):
        """修复后的置乱操作，确保交换唯一且可逆"""
        M, N = A.shape
        B = A.copy()
        L = np.sum(A, axis=1, dtype=np.int64)
        H = np.sum(A.T, axis=1, dtype=np.int64)
        self.swap_info = []
        swapped = np.zeros((M, N), dtype=bool)

        for i in range(M):
            for j in range(N):
                if swapped[i, j]:
                    continue  # 当前像素已参与交换，跳过

                m = int((U[i, j] + H[int(Z[i, j]) % N]) % M)
                n = int((V[i, j] + L[int(W[i, j]) % M]) % N)

                if (m == i and n == j) or swapped[m, n]:
                    continue  # 自交换或目标已交换，跳过

                # 执行交换
                B[i, j], B[m, n] = B[m, n], B[i, j]
                self.swap_info.append((i, j, m, n))
                swapped[i, j] = True
                swapped[m, n] = True

        return B

    def _inverse_scrambling_operation(self, B, U, V, Z, W):
        """逆置乱操作"""
        A = B.copy()
        # 按相反顺序执行交换
        for i, j, m, n in reversed(self.swap_info):
            # print(f"逆置乱操作: 交换 ({i}, {j}) 和 ({m}, {n})")
            # print(f"  交换前 A[{i}, {j}] = {A[i, j]}, A[{m}, {n}] = {A[m, n]}")

            A[i, j], A[m, n] = A[m, n], A[i, j]

            # print(f"  交换后 A[{i}, {j}] = {A[i, j]}, A[{m}, {n}] = {A[m, n]}")

        return A

    # ============================

    def encrypt(self, image_path, save_path=None):
        """改进的加密方法，增加了置乱（像素位置置换）功能"""
        try:
            img = Image.open(image_path).convert('L')
            image = np.array(img)
            M, N = image.shape

            if self.initial_values is None:
                self.generate_main_key(image_path)
            X, Y, Z, W, U, V, T = self._generate_chaos_sequences(M, N)

            A = np.zeros_like(image)
            for i in range(M):
                for j in range(N):
                    rule_idx = T[i, j]
                    pixel_dna = self._dna_operations(image[i, j], 0, rule_idx, 'encode')
                    chaos_dna = self._dna_operations(int(X[i, j]), 0, rule_idx, 'encode')
                    xor_dna = self._dna_xor(pixel_dna, chaos_dna, rule_idx)
                    A[i, j] = self._dna_operations(xor_dna, 0, rule_idx, 'decode')

            B = self._scrambling_operation(A, U, V, Z, W)

            C = np.zeros_like(B)
            C[M - 1, N - 1] = np.uint8((int(B[M - 1, N - 1]) ^ int(Y[M - 1, N - 1]) ^ int(self.r1)) % 256)

            prev_C = self.r1
            for i in range(M):
                for j in range(N):
                    if j == 0:
                        C[i, j] = np.uint8((int(B[i, j]) + int(prev_C) + int(Y[i, j])) % 256)
                    else:
                        C[i, j] = np.uint8((int(B[i, j]) + int(C[i, j - 1]) + int(Y[i, j])) % 256)
                prev_C = C[i, -1]

            encrypted_img = Image.fromarray(C.astype(np.uint8))
            if save_path:
                encrypted_img.save(save_path)
            return encrypted_img

        except Exception as e:
            raise ValueError(f"加密失败: {str(e)}")

    def decrypt(self, encrypted_image_path, initial_values=None, save_path=None):
        """改进的解密方法，包含逆扩散、逆置乱和逆DNA操作"""
        try:
            if initial_values is not None:
                self.initial_values = initial_values
            if self.initial_values is None:
                raise ValueError("需要提供初始值用于解密")

            encrypted_img = Image.open(encrypted_image_path).convert('L')
            C = np.array(encrypted_img)
            M, N = C.shape

            X, Y, Z, W, U, V, T = self._generate_chaos_sequences(M, N)

            B = np.zeros_like(C)
            prev_C = self.r1
            for i in range(M):
                for j in range(N):
                    if j == 0:
                        B[i, j] = np.uint8((int(C[i, j]) - int(prev_C) - int(Y[i, j])) % 256)
                    else:
                        B[i, j] = np.uint8((int(C[i, j]) - int(C[i, j - 1]) - int(Y[i, j])) % 256)
                prev_C = C[i, -1]

            A_recovered = self._inverse_scrambling_operation(B, U, V, Z, W)

            original = np.zeros_like(A_recovered)
            for i in range(M):
                for j in range(N):
                    rule_idx = T[i, j]
                    xor_dna = self._dna_operations(A_recovered[i, j], 0, rule_idx, 'encode')
                    chaos_dna = self._dna_operations(int(X[i, j]), 0, rule_idx, 'encode')
                    pixel_dna = self._dna_xor(xor_dna, chaos_dna, rule_idx)
                    original[i, j] = self._dna_operations(pixel_dna, 0, rule_idx, 'decode')

            decrypted_img = Image.fromarray(original.astype(np.uint8))
            if save_path:
                decrypted_img.save(save_path)
            return decrypted_img

        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")

    def analyze_security(self, original_path, encrypted_path):
        """安全性分析"""
        # 直方图分析
        self._plot_histograms(original_path, encrypted_path)

        # 相邻像素相关性分析
        print("\n原始图像相邻像素相关性:")
        self._pixel_correlation(original_path)

        print("\n加密图像相邻像素相关性:")
        self._pixel_correlation(encrypted_path)

        # 密钥敏感性测试
        print("\n密钥敏感性测试:")
        self._key_sensitivity_test(original_path)

    def _plot_histograms(self, original_path, encrypted_path):
        """绘制直方图"""
        original_img = Image.open(original_path).convert('L')
        encrypted_img = Image.open(encrypted_path).convert('L')

        plt.figure(figsize=(12, 6))

        plt.subplot(1, 2, 1)
        plt.hist(np.array(original_img).flatten(), bins=256, range=(0, 256), color='blue')
        plt.title('Original Image Histogram')
        plt.xlabel('Pixel Value')
        plt.ylabel('Frequency')

        plt.subplot(1, 2, 2)
        plt.hist(np.array(encrypted_img).flatten(), bins=256, range=(0, 256), color='red')
        plt.title('Encrypted Image Histogram')
        plt.xlabel('Pixel Value')
        plt.ylabel('Frequency')

        plt.tight_layout()
        plt.show()

    def _pixel_correlation(self, image_path, num_pairs=5000):
        """分析相邻像素相关性（分别采样不同方向的随机对）"""
        img = Image.open(image_path).convert('L')
        data = np.array(img)
        M, N = data.shape

        # 水平方向
        x_h = data[:, :-1].flatten()
        y_h = data[:, 1:].flatten()
        # 垂直方向
        x_v = data[:-1, :].flatten()
        y_v = data[1:, :].flatten()
        # 对角线方向
        x_d = data[:-1, :-1].flatten()
        y_d = data[1:, 1:].flatten()

        # 分别随机选择像素对
        idx_h = np.random.choice(len(x_h), min(num_pairs, len(x_h)), replace=False)
        idx_v = np.random.choice(len(x_v), min(num_pairs, len(x_v)), replace=False)
        idx_d = np.random.choice(len(x_d), min(num_pairs, len(x_d)), replace=False)

        # 计算相关系数
        corr_h = np.corrcoef(x_h[idx_h], y_h[idx_h])[0, 1]
        corr_v = np.corrcoef(x_v[idx_v], y_v[idx_v])[0, 1]
        corr_d = np.corrcoef(x_d[idx_d], y_d[idx_d])[0, 1]

        print(f"水平方向相关系数: {corr_h:.6f}")
        print(f"垂直方向相关系数: {corr_v:.6f}")
        print(f"对角线方向相关系数: {corr_d:.6f}")

        # 绘制散点图
        plt.figure(figsize=(15, 5))

        plt.subplot(1, 3, 1)
        plt.scatter(x_h[idx_h], y_h[idx_h], s=1)
        plt.title(f'Horizontal Correlation: {corr_h:.4f}')
        plt.xlabel('Pixel (i,j)')
        plt.ylabel('Pixel (i,j+1)')

        plt.subplot(1, 3, 2)
        plt.scatter(x_v[idx_v], y_v[idx_v], s=1)
        plt.title(f'Vertical Correlation: {corr_v:.4f}')
        plt.xlabel('Pixel (i,j)')
        plt.ylabel('Pixel (i+1,j)')

        plt.subplot(1, 3, 3)
        plt.scatter(x_d[idx_d], y_d[idx_d], s=1)
        plt.title(f'Diagonal Correlation: {corr_d:.4f}')
        plt.xlabel('Pixel (i,j)')
        plt.ylabel('Pixel (i+1,j+1)')

        plt.tight_layout()
        plt.show()

    def _key_sensitivity_test(self, image_path, delta=1e-8):  # 将delta从1e-16调整为1e-8
        """密钥敏感性测试"""
        # 原始加密
        self.generate_main_key(image_path)
        original_img = Image.open(image_path).convert('L')
        encrypted1 = self.encrypt(image_path)
        arr1 = np.array(encrypted1)

        # 微调初始值后加密
        x0, y0, z0, w0 = self.initial_values
        self.initial_values = [x0 + delta, y0, z0, w0]
        encrypted2 = self.encrypt(image_path)
        arr2 = np.array(encrypted2)

        # 计算NPCR和UACI
        diff = arr1 != arr2
        npcr = np.sum(diff) / arr1.size * 100
        uaci = np.mean(np.abs(arr1.astype(int) - arr2.astype(int))) / 255 * 100

        print(f"NPCR (像素变化率): {npcr:.6f}% (理想值≈99.6094%)")
        print(f"UACI (平均变化强度): {uaci:.6f}% (理想值≈33.4635%)")

        # 恢复原始初始值
        self.initial_values = [x0, y0, z0, w0]

        return npcr, uaci

    def test_encryption(self, image_path):
        """完整的加密解密测试"""
        print("=== 开始加密解密测试 ===")

        # 生成密钥
        print("生成密钥...")
        initial_values, main_key = self.generate_main_key(image_path)

        # 加密
        print("加密图像...")
        encrypted = self.encrypt(image_path, "encrypted.png")

        # 解密
        print("解密图像...")
        decrypted = self.decrypt("encrypted.png", initial_values, "decrypted.png")

        # 验证
        original = np.array(Image.open(image_path).convert('L'))
        decrypted_array = np.array(decrypted)

        if original.shape != decrypted_array.shape:
            print("错误: 解密图像尺寸不匹配")
            return False

        diff = np.sum(np.abs(original.astype(int) - decrypted_array.astype(int)))
        similarity = np.mean(original == decrypted_array) * 100

        print(f"解密验证:")
        print(f"- 像素差异总和: {diff}")
        print(f"- 像素匹配率: {similarity:.2f}%")

        if diff == 0:
            print("成功: 解密图像与原始图像完全相同!")
            result = True
        elif similarity > 99.9:
            print("基本成功: 解密图像与原始图像几乎相同")
            result = True
        else:
            print("失败: 解密图像与原始图像不一致")
            result = False

        # 调用安全性分析函数
        print("\n开始安全性分析...")
        self.analyze_security(image_path, "encrypted.png")
        return result




if __name__ == "__main__":
    # 初始化加密器
    encryptor = ChaosImageEncryptor()

    # 测试图像路径
    test_image = "Lena.png"

    # 运行完整测试
    success = encryptor.test_encryption(test_image)

    if success:
        print("\n加密解密测试成功完成!")
    else:
        print("\n加密解密测试失败，请检查代码!")

