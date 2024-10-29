import sys
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from text.symbols2 import arpa

class ArpabetSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.normal_text_format = QTextCharFormat()
        self.valid_arpa_format = QTextCharFormat()
        self.valid_arpa_format.setForeground(QColor("cyan"))
        self.invalid_arpa_format = QTextCharFormat()
        self.invalid_arpa_format.setForeground(QColor("red"))

    def highlightBlock(self, text):
        in_arpa_block = False  # Tracks if we're inside an ARPAbet block
        start_idx = 0  # Start index of the current segment

        i = 0
        while i < len(text):
            char = text[i]

            if char == "{":
                # Handle start of ARPAbet block
                if in_arpa_block:
                    # Already in an ARPAbet block, treat text as normal up to this point
                    self.setFormat(start_idx, i - start_idx, self.normal_text_format)
                start_idx = i
                in_arpa_block = True

            elif char == "}" and in_arpa_block:
                # Handle end of ARPAbet block
                self._apply_arpa_format(text, start_idx + 1, i - start_idx - 1)
                start_idx = i + 1  # Update for next text segment
                in_arpa_block = False

            elif not in_arpa_block and char != "{":
                # Normal text outside of ARPAbet blocks
                if i == len(text) - 1:  # End of line
                    self.setFormat(start_idx, i - start_idx + 1, self.normal_text_format)
                elif text[i + 1] == "{":
                    # Format normal text up to the next ARPAbet block
                    self.setFormat(start_idx, i - start_idx + 1, self.normal_text_format)
                    start_idx = i + 1

            i += 1

        # If we end the line still in an ARPAbet block, treat as incomplete
        if in_arpa_block:
            self._apply_arpa_format(text, start_idx + 1, len(text) - start_idx - 1)

    def _apply_arpa_format(self, text, start, length):
        # Extract and validate each ARPAbet code within the given range
        arpa_text = text[start:start + length].strip()
        words = arpa_text.split()

        current_index = start  # Start index within the block
        for word in words:
            if word in arpa:
                # Valid ARPAbet code
                self.setFormat(current_index, len(word), self.valid_arpa_format)
            else:
                # Invalid ARPAbet code
                self.setFormat(current_index, len(word), self.invalid_arpa_format)
            current_index += len(word) + 1  # Move index to next word (+1 for space)