variable "name_prefix" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

resource "aws_s3_bucket" "knowledge_corpus" {
  bucket = "${var.name_prefix}-gie-knowledge-corpus"
  tags   = var.tags
}

output "corpus_bucket" {
  value = aws_s3_bucket.knowledge_corpus.bucket
}
