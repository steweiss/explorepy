import numpy as np


class ImuCalib:
    def __init__(self):
        self.w_acc = [[0], [0], [0]]
        self.w_mag = [[0], [0], [0]]
        self.w_gyro = [[0], [0], [0]]
        self.gyroscale = 0.07

        self.M_acc = np.identity(3)
        self.M_mag = np.identity(3)
        self.M_gyro = np.identity(3)

    def acc_calib(self, accdata):
        accdata = np.asarray(accdata)
        ax = accdata[:, 0]
        ay = accdata[:, 1]
        az = accdata[:, 2]
        n = np.size(ax)
        x = [ax, ay, az]
        x = np.asarray(x)

        """Perform Ellipsoid fitting, least squares fit"""

        m_meas = np.column_stack((np.transpose(x)*np.transpose(x), ax*2*ay, ax*2*az,
                                 ay*2*az, np.transpose(x)*2))
        print(m_meas.shape)
        d = np.ones((n, 1))

        """Singular value decomposition"""

        u, s, v = np.linalg.svd(m_meas, full_matrices=False)

        p = np.dot(np.dot(np.dot(np.transpose(v), np.linalg.inv(np.identity(9)*s)), np.transpose(u)), d)
        print(p)
        A_t = np.row_stack(([p[0][0], 0, 0], [0, p[1][0], 0], [0, 0, p[2][0]]))
        print(A_t)
        b_t = [[2*p[6][0], 2*p[7][0], 2*p[8][0]]]
        print(b_t)
        #t = np.dot(np.dot(np.transpose(x), A_t), x)+np.dot(np.transpose(b_t), x)

        """Ellipsoid offset w"""

        self.w_acc = -0.5*np.dot(np.dot(np.linalg.inv(np.dot(np.transpose(A_t), A_t)), np.transpose(A_t)), np.transpose(b_t))

        """General ellipsoid matrix A"""

        A = A_t
        b = np.asarray(b_t) * 0.5
        c = -1;

        A_ = np.column_stack((np.row_stack((A, b)), np.row_stack((np.transpose(b), c))))
        print(A_)
        T = np.append(np.append(np.identity(3), self.w_acc, axis=1), [[0, 0, 0, 1]], axis=0)
        Aroof = np.dot(np.dot(np.transpose(T), A_), T)

        Afit = -(1/Aroof[3, 3])*np.array(Aroof[0:3, 0:3])
        u, s, v = np.linalg.svd(Afit, full_matrices=False)

        """Find Model matrix"""

        self.M_acc = np.dot(np.sqrt(np.identity(s.size)*s), np.transpose(v))
        print("Done and Done")
        y = np.dot(self.M_acc, np.subtract(x, self.w_acc))
        print(y)
        print(y.shape)
        return self.M_acc, self.w_acc

    def mag_Calib(self, magdata):
        magdata = np.asarray(magdata)
        mx = magdata[:, 0]
        my = magdata[:, 1]
        mz = magdata[:, 2]
        n = np.size(mx)
        x = [mx, my, mz]
        x = np.asarray(x)

        """Perform Ellipsoid fitting, least squares fit"""

        m_meas = np.column_stack((np.transpose(x)*np.transpose(x), mx*2*my, mx*2*mz,
                                 my*2*mz, np.transpose(x)*2))
        print(m_meas)
        d = np.ones((n, 1))

        """Singular value decomposition"""

        p = np.dot(np.dot(np.linalg.inv(np.dot(np.transpose(m_meas), m_meas)), np.transpose(m_meas)), d)
        print(p)
        A_t = np.row_stack(([p[0][0], p[3][0], p[4][0]], [p[3][0], p[1][0], p[5][0]], [p[4][0], p[5][0], p[2][0]]))
        print(A_t)
        b_t = [[2*p[6][0], 2*p[7][0], 2*p[8][0]]]

        #t = np.dot(np.dot(np.transpose(x), A_t), x)+np.dot(np.transpose(b_t), x)

        """Ellipsoid offset w"""

        self.w_mag = -0.5*np.dot(np.dot(np.linalg.inv(np.dot(np.transpose(A_t), A_t)), np.transpose(A_t)), np.transpose(b_t))
        """General ellipsoid matrix A"""

        A = A_t
        b = np.asarray(b_t) * 0.5
        c = -1;

        A_ = np.column_stack((np.row_stack((A, b)), np.row_stack((np.transpose(b), c))))
        T = np.append(np.append(np.identity(3), self.w_mag, axis=1), [[0, 0, 0, 1]], axis=0)
        Aroof = np.dot(np.dot(np.transpose(T), A_), T)
        Afit = -(1/Aroof[3, 3])*np.array(Aroof[0:3, 0:3])
        u, s, v = np.linalg.svd(Afit, full_matrices=False)

        """Find Model matrix"""

        self.M_mag = np.dot(np.sqrt(np.identity(s.size)*s), np.transpose(v))
        y = np.dot(np.transpose(self.M_mag), np.subtract(x, self.w_mag))
        print(y)
        print(y.shape)
        return y

    def gyro_Calib(self, gyrodata):
        gyrodata = np.asarray(gyrodata)
        gx = gyrodata[:, 0]
        gy = gyrodata[:, 1]
        gz = gyrodata[:, 2]
        n = np.size(gx)
        x = [gx, gy, gz]
        x = np.asarray(x)

        """x = x*self.gyroscale"""
        self.w_gyro = np.mean(x, axis=1)
        print(self.w_gyro)
        """self.M_gyro = self.M_gyro*self.gyroscale"""
        y = np.dot(self.M_gyro, np.subtract(x, np.transpose([self.w_gyro])))
        print(y)
        return y
