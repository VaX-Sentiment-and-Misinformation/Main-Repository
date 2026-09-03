MODEL_NAME = "bert-base-uncased"
NUM_LABELS = 2  # 0 = not misinfo, 1 = misinfo
MAX_LEN = 128
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 2e-5

DATA_CSV = "data/misinformation/labelledTweets.csv"
TEXT_COL = "text"
LABEL_COL = "is_misinfo"

OUTPUT_DIR = "./savedModel"
TEST_SIZE = 0.3  # 20% held out for validation
RANDOM_SEED = 42