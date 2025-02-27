# Copyright 2023, MetaQuotes Ltd.
# https://www.mql5.com

# библиотеки Python
import MetaTrader5 as mt5
import tensorflow as tf
import numpy as np
import pandas as pd

# входные параметры
inp_model_name = "model.eurusd.H1.275.onnx"
inp_history_size = 275

if not mt5.initialize():
    print("initialize() не удалось, код ошибки =", mt5.last_error())
    quit()

# сохраним onnx-файл рядом со скриптом как ресурс
from sys import argv
data_path = argv[0]
last_index = data_path.rfind("\\") + 1
data_path = data_path[0:last_index]
print("путь для сохранения onnx модели", data_path)

# и сохраним в папке MQL5\Files для использования как файл
terminal_info = mt5.terminal_info()
file_path = terminal_info.data_path + "\\MQL5\\Files\\"
print("путь для сохранения onnx модели", file_path)

# устанавливаем начальную и конечную даты для исторических данных
from datetime import timedelta, datetime
end_date = datetime.now()
# end_date = datetime(2023, 1, 1, 0)
start_date = end_date - timedelta(days=inp_history_size)

# получаем котировки
eurusd_rates = mt5.copy_rates_range("EURUSD", mt5.TIMEFRAME_H1, start_date, end_date)

# выводим начальную и конечную даты
print("начальная дата данных =", start_date)
print("конечная дата данных =", end_date)

# создаем DataFrame
df = pd.DataFrame(eurusd_rates)

# агрегируем только цены закрытия
data = df.filter(['close']).values

# масштабируем данные
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(data)

# размер обучающей выборки 80% от данных
training_size = int(len(scaled_data) * 0.80)
print("Размер обучающей выборки:", training_size)
train_data_initial = scaled_data[0:training_size, :]
test_data_initial = scaled_data[training_size:, :1]

# разбиваем последовательность на образцы
def split_sequence(sequence, n_steps):
    X, y = list(), list()
    for i in range(len(sequence)):
        # находим конец этого шаблона
        end_ix = i + n_steps
        # проверяем пределы последовательности
        if end_ix > len(sequence) - 1:
            break
        # собираем входные и выходные части шаблона
        seq_x, seq_y = sequence[i:end_ix], sequence[end_ix]
        X.append(seq_x)
        y.append(seq_y)
    return np.array(X), np.array(y)

# разделение на выборки
time_step = inp_history_size
x_train, y_train = split_sequence(train_data_initial, time_step)
x_test, y_test = split_sequence(test_data_initial, time_step)

# изменение формы входных данных на [образцы, временные шаги, признаки] для LSTM
x_train = x_train.reshape(x_train.shape[0], x_train.shape[1], 1)
x_test = x_test.reshape(x_test.shape[0], x_test.shape[1], 1)

import tensorflow as tf
from keras.models import Model
from keras.layers import Dense, Activation, Conv1D, MaxPooling1D, Dropout, LSTM, Input
from keras.regularizers import l2
from tensorflow.keras.metrics import RootMeanSquaredError
import tf2onnx

# Проверка доступности GPU
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(e)

# Определение входного слоя
inputs = Input(shape=(inp_history_size, 1))

# Добавляем Conv1D
x = Conv1D(filters=256, kernel_size=2, activation='relu', padding='same')(inputs)
x = MaxPooling1D(pool_size=2)(x)

# Добавляем LSTM
x = LSTM(100, return_sequences=True)(x)
x = Dropout(0.3)(x)

x = LSTM(100, return_sequences=False)(x)
x = Dropout(0.3)(x)

# Выходной слой
outputs = Dense(units=1, activation='sigmoid')(x)

# Создание модели
model = Model(inputs=inputs, outputs=outputs)

# Компиляция модели
model.compile(optimizer='adam', loss='mse', metrics=[RootMeanSquaredError(name='rmse')])

# Обучение модели 100 эпох
history = model.fit(x_train, y_train, epochs=100, validation_data=(x_test, y_test), batch_size=32, verbose=2)

# Оценка данных обучения
train_loss, train_rmse = model.evaluate(x_train, y_train, batch_size=32)
print(f"train_loss={train_loss:.3f}")
print(f"train_rmse={train_rmse:.3f}")

# Оценка тестовых данных
test_loss, test_rmse = model.evaluate(x_test, y_test, batch_size=32)
print(f"test_loss={test_loss:.3f}")
print(f"test_rmse={test_rmse:.3f}")

# Сохранение модели в формате ONNX
output_path = data_path + inp_model_name

# Конвертация модели в ONNX
spec = (tf.TensorSpec((None, inp_history_size, 1), tf.float32, name="input"),)
onnx_model, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)

# Сохранение модели
with open(output_path, "wb") as f:
    f.write(onnx_model.SerializeToString())

print(f"модель сохранена в {output_path}")

# завершение
mt5.shutdown()