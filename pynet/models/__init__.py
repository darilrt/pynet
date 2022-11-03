
class MessageModel:
    def __init__(self, m_type, m_data, token = ""):
        self.type = m_type
        self.data = m_data
        self.token = token
    
    def to_dict(self):
        return {
            "type": self.type,
            "data": self.data
        }
