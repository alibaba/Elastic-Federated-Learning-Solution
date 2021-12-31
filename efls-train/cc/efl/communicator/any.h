/* Copyright (C) 2016-2021 Alibaba Group Holding Limited
  
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
==============================================================================*/

#ifndef EFL_ANY_H_
#define EFL_ANY_H_

#include <typeindex>

namespace tensorflow {
namespace efl {

class Any {
 public:
  Any()
    : type_index_(std::type_index(typeid(void))) {}

  Any(const Any& that)
    : base_ptr_(that.Clone()),
      type_index_(that.type_index_) {}

  Any(Any&& that) noexcept
    : base_ptr_(std::move(that.base_ptr_)),
      type_index_(that.type_index_) {}

  template<typename T>
  explicit Any(const T& value)
    : base_ptr_(new Derived<typename std::decay<T>::type>(value)),
      type_index_(std::type_index(typeid(typename std::decay<T>::type))) {}

  Any& operator=(const Any& a) {
    if (base_ptr_ != a.base_ptr_) {
      base_ptr_ = a.Clone();
      type_index_ = a.type_index_;
    }
    return *this;
  }

  // Null pointer check.
  bool IsNull() const {
    return !bool(base_ptr_);
  }

  // Get content from Any as type T.
  template<typename T>
  T& Cast() {
    if (type_index_ != std::type_index(typeid(T))) { // Check type.
      std::string err_str("can not cast ");
      err_str += type_index_.name();
      err_str += " to ";
      err_str += std::type_index(typeid(T)).name();
      throw std::logic_error(err_str);
    }
    auto derived = dynamic_cast<Derived<T>*>(base_ptr_.get());
    return derived->value_;
  }

 private:
  // Base Class.
  class Base;
  typedef std::unique_ptr<Base> BasePtr;

  class Base {
   public:
    virtual ~Base() = default;
    virtual BasePtr Clone() const = 0;
  };

  // Derived Class used to store value.
  template<typename T>
  class Derived final : public Base {
   public:
    explicit Derived(const T& value)
      : value_(value) {}

    BasePtr Clone() const override {
      return BasePtr(new Derived(value_));
    }

   private:
    friend class Any;

    T value_; // value to store.
  };

  BasePtr Clone() const {
    return base_ptr_ == nullptr ? nullptr : base_ptr_->Clone();
  }

  BasePtr base_ptr_;
  std::type_index type_index_;
};

// Store any infos as kv-pairs.
class AnyMap {
 public:
  // Insert a value to map.
  void Add(const string& key, const Any& val) {
    map_[key] = val;
  }

  // Get a value from map.
  Any Get(const string& key) const {
    auto iter = map_.find(key);
    if (iter == map_.end()) {
      return Any();
    } else {
      return iter->second;
    }
  }

  // Remove a value from map.
  void Remove(const string& key) {
    map_.erase(key);
  }

 private:
  std::unordered_map<string, Any> map_;
};

} // efl
} // tensorflow

#endif // EFL_ANY_H_
